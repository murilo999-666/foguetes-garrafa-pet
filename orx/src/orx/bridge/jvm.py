"""Inicialização da JVM com o OpenRocket 24.12 em modo headless.

Verificado contra a instalação local (ver scripts/probe_bridge.py):
- 1 JVM por processo (limitação do JPype); paralelismo = multiprocessing.
- Injeção Guice: CoreServicesModule + PluginModule (sem GUI), e o banco de
  motores é carregado via CoreMotorDatabaseProvider (bloqueia até terminar)
  e registrado num child injector — o GuiModule abriria diálogos Swing.
"""

from __future__ import annotations

import threading

import jpype
import jpype.imports  # noqa: F401  (habilita import de pacotes Java após startJVM)

from ..config.loader import PathsConfig
from ..utils.logging import get_logger

log = get_logger("bridge.jvm")

_lock = threading.Lock()
_started = False
_motor_db = None


def is_started() -> bool:
    return _started


def _jvm_options() -> list[str]:
    """Opções da JVM, enxutas para rodar MUITAS JVMs em paralelo no Windows.

    Cada worker do pool é uma JVM. Com o G1 e -Xmx1024m a JVM COMMITA ~254 MB
    logo na partida (heap inicial = 1/64 da RAM); seis workers estouravam o
    limite de commit do Windows e a partida morria com
    "os::commit_memory ... arquivo de paginação é muito pequeno" (errno 1455),
    derrubando a busca no meio. As simulações do OpenRocket usam pouca memória,
    então: heap inicial minúsculo que cresce sob demanda + SerialGC (o G1
    reserva região por região e mantém estruturas por thread que não pagam a
    pena aqui). Ajustável por ORX_JVM_OPTS se a máquina for outra.
    """
    import os

    extra = os.environ.get("ORX_JVM_OPTS", "").split()
    return [
        "-Djava.awt.headless=true",
        "-Xms32m",
        os.environ.get("ORX_JVM_XMX", "-Xmx768m"),
        "-XX:+UseSerialGC",
        "-XX:MaxMetaspaceSize=192m",
        "-XX:-UsePerfData",          # evita arquivo hsperfdata por JVM
        *extra,
    ]


def ensure_jvm(paths: PathsConfig | None = None) -> None:
    """Inicia a JVM + injeção do OpenRocket uma única vez por processo."""
    global _started, _motor_db
    with _lock:
        if _started:
            return
        paths = paths or PathsConfig()
        jar = paths.resolve_jar()
        jvm = paths.resolve_jvm()
        log.info("Iniciando JVM: %s", jar)

        if not jpype.isJVMStarted():
            jpype.startJVM(jvm, *_jvm_options(), classpath=[jar])

        # silencia o logback do OpenRocket (INFO é muito verboso p/ milhares de sims)
        try:
            root_logger = jpype.JClass("org.slf4j.LoggerFactory").getLogger("ROOT")
            root_logger.setLevel(jpype.JClass("ch.qos.logback.classic.Level").ERROR)
        except Exception:  # pragma: no cover — backend de log diferente
            log.debug("não foi possível ajustar o nível do logback")

        from com.google.inject import Guice  # type: ignore
        from info.openrocket.core.plugin import PluginModule  # type: ignore
        from info.openrocket.core.startup import Application  # type: ignore
        from info.openrocket.swing.utils import CoreServicesModule  # type: ignore

        base_injector = Guice.createInjector(CoreServicesModule(), PluginModule())
        Application.setInjector(base_injector)

        from info.openrocket.core.database import MotorDatabaseLoader  # type: ignore
        from info.openrocket.core.database.motor import (  # type: ignore
            MotorDatabase,
            ThrustCurveMotorSetDatabase,
        )
        from info.openrocket.core.startup.providers import (  # type: ignore
            CoreMotorDatabaseProvider,
        )

        loader = MotorDatabaseLoader()
        loader.startLoading()
        motor_db = CoreMotorDatabaseProvider(loader).get()  # bloqueia até carregar
        log.info("Banco de motores carregado: %d conjuntos", motor_db.getMotorSets().size())

        from jpype import JImplements, JOverride

        @JImplements("com.google.inject.Module")
        class _MotorDatabaseModule:
            @JOverride
            def configure(self, binder):
                binder.bind(MotorDatabase).toInstance(motor_db)
                binder.bind(ThrustCurveMotorSetDatabase).toInstance(motor_db)

        Application.setInjector(base_injector.createChildInjector(_MotorDatabaseModule()))
        _motor_db = motor_db
        _started = True
        log.info("OpenRocket headless pronto")


def motor_database():
    """ThrustCurveMotorSetDatabase carregado (exige ensure_jvm antes)."""
    if not _started:
        raise RuntimeError("JVM não iniciada; chame ensure_jvm() primeiro")
    return _motor_db
