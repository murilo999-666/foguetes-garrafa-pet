"""Dev tool: reflect over OpenRocket 24.12 classes and dump the public API we
intend to call, so the parameter layer is built on verified method names."""

import jpype
import jpype.imports

JAR = r"C:\Program Files\OpenRocket\jar\OpenRocket-24.12.jar"
JVM_DLL = r"C:\Program Files\OpenRocket\jre\bin\server\jvm.dll"

jpype.startJVM(JVM_DLL, "-Djava.awt.headless=true", classpath=[JAR])

CLASSES = [
    "info.openrocket.core.document.Simulation",
    "info.openrocket.core.simulation.FlightData",
    "info.openrocket.core.simulation.FlightDataBranch",
    "info.openrocket.core.rocketcomponent.DeploymentConfiguration",
    "info.openrocket.core.rocketcomponent.FlightConfiguration",
]

ENUMS = [
    "info.openrocket.core.rocketcomponent.Transition$Shape",
    "info.openrocket.core.rocketcomponent.position.AxialMethod",
    "info.openrocket.core.simulation.FlightEvent$Type",
    "info.openrocket.core.rocketcomponent.DeploymentConfiguration$DeployEvent",
]

for cname in CLASSES:
    cls = jpype.JClass(cname)
    print(f"\n=== {cname} ===")
    if cname.endswith(("Simulation", "Configuration")):
        for c in cls.class_.getConstructors():
            print("  CTOR:", c)
    methods = sorted(
        {
            str(m.getName())
            + "("
            + ",".join(str(p.getSimpleName()) for p in m.getParameterTypes())
            + ")"
            for m in cls.class_.getMethods()
            if str(m.getDeclaringClass().getName()).startswith("info.openrocket")
            and (
                str(m.getName()).startswith("set")
                or str(m.getName()).startswith("get")
                or str(m.getName()) in ("simulate", "copy", "clone")
            )
        }
    )
    for m in methods:
        print("  ", m)

for ename in ENUMS:
    cls = jpype.JClass(ename)
    print(f"\n=== ENUM {ename} ===")
    try:
        print("  ", [str(v) for v in cls.values()])
    except Exception as e:
        print("   (no values):", e)

fdt = jpype.JClass("info.openrocket.core.simulation.FlightDataType")
consts = [f.getName() for f in fdt.class_.getFields() if str(f.getName()).startswith("TYPE_")]
print("\n=== FlightDataType constants ===")
print(sorted(str(c) for c in consts))
