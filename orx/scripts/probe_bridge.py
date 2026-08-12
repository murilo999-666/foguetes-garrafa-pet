"""Smoke test: start OpenRocket 24.12 headless via JPype and run one simulation.

Verifies, before any architecture is built on top:
  1. The bundled JDK 17 jvm.dll can host JPype.
  2. Guice injection (GuiModule + PluginModule) initializes headless.
  3. An .ork file loads, a simulation runs, and flight data is readable.
"""

import sys

import jpype
import jpype.imports

JAR = r"C:\Program Files\OpenRocket\jar\OpenRocket-24.12.jar"
JVM_DLL = r"C:\Program Files\OpenRocket\jre\bin\server\jvm.dll"
ORK = r"C:\Users\muril\openrocket-optimizer\data\designs\A simple model rocket.ork"


def main() -> int:
    jpype.startJVM(JVM_DLL, "-Djava.awt.headless=true", classpath=[JAR])

    from com.google.inject import Guice
    from info.openrocket.core.plugin import PluginModule
    from info.openrocket.core.startup import Application
    from info.openrocket.swing.utils import CoreServicesModule

    base_injector = Guice.createInjector(CoreServicesModule(), PluginModule())
    Application.setInjector(base_injector)

    from info.openrocket.core.database import MotorDatabaseLoader
    from info.openrocket.core.database.motor import (
        MotorDatabase,
        ThrustCurveMotorSetDatabase,
    )
    from info.openrocket.core.startup.providers import CoreMotorDatabaseProvider

    loader = MotorDatabaseLoader()
    loader.startLoading()
    motor_db = CoreMotorDatabaseProvider(loader).get()  # blocks until loaded
    print(f"[ok] motor database loaded: {motor_db.getMotorSets().size()} motor sets")

    from jpype import JImplements, JOverride

    @JImplements("com.google.inject.Module")
    class MotorDatabaseModule:
        @JOverride
        def configure(self, binder):
            binder.bind(MotorDatabase).toInstance(motor_db)
            binder.bind(ThrustCurveMotorSetDatabase).toInstance(motor_db)

    injector = base_injector.createChildInjector(MotorDatabaseModule())
    Application.setInjector(injector)
    print("[ok] JVM + Guice injector initialized (headless, with motor db)")

    from java.io import File
    from info.openrocket.core.file import GeneralRocketLoader

    doc = GeneralRocketLoader(File(ORK)).load()
    rocket = doc.getRocket()
    print(f"[ok] loaded rocket: {rocket.getName()}")

    sims = doc.getSimulations()
    print(f"[ok] document has {sims.size()} simulations")
    sim = sims.get(0)
    print(f"     running: {sim.getName()}")
    sim.simulate()

    data = sim.getSimulatedData()
    branch = data.getBranch(0)

    from info.openrocket.core.simulation import FlightDataType

    import numpy as np

    alt = np.array(list(branch.get(FlightDataType.TYPE_ALTITUDE)))
    vel = np.array(list(branch.get(FlightDataType.TYPE_VELOCITY_TOTAL)))
    print(f"[ok] apogee: {alt.max():.1f} m")
    print(f"[ok] max velocity: {vel.max():.1f} m/s")
    print(f"[ok] flight time: {data.getFlightTime():.1f} s")
    print("[ok] bridge works end to end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
