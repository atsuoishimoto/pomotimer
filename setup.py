from distutils.core import setup
import py2exe


options = {
    "dll_excludes": ["WINHTTP.dll", "w9xpopen.exe"],
    "excludes": ["Tkconstants","Tkinter","tcl", "doctest", "setuptools", "subprocess", "select", "unicodedata", "bz2"],
    "compressed":1,
    "optimize":2,
    "xref":1,
}


RT_MANIFEST = 24

class Target:
    MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
  version="1.0.0.0"
  processorArchitecture="X86"
  name="pomotimer.exe"
/>
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v2">
  <security>
    <requestedPrivileges>
      <requestedExecutionLevel
        level="asInvoker"
        uiAccess="false"/>
    </requestedPrivileges>
  </security>
</trustInfo>
<description>Pomo Timer</description>
<dependency>
  <dependentAssembly>
    <assemblyIdentity
      type="win32"
      name="Microsoft.Windows.Common-Controls"
      version="6.0.0.0"
      processorArchitecture="X86"
      publicKeyToken="6595b64144ccf1df"
      language="*"
    />
  </dependentAssembly>
</dependency>

<dependency>
  <dependentAssembly>
    <assemblyIdentity type="win32" name="Microsoft.VC90.CRT" version="9.0.30729.4148" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b" />
  </dependentAssembly>
</dependency>
</assembly>
"""
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.script = "pomotimer.py"
        self.version = "0.0.2"
        self.description = "pomotimer"
        self.company_name = "Atsuo Ishimoto"
        self.name = "Pomodoro Timer"
        self.other_resources = [(RT_MANIFEST, 1, self.MANIFEST)]
        self.icon_resources = [(1, "pomotimer.ico")]


setup(name='pomotimer',
      version="0.0.2",
      data_files=[
          ('', 
              ['README.TXT', 'COPYING',
               'pomotimer.ico', 'close.ico', 'pause.ico', 
               'pomotimer_pause.ico', 'pomotimer_run.ico', 
               'pomotimer_timeout.ico', 'start.ico', 'stop.ico',
               ]),
      ],
      windows = [Target()],
      options = {'py2exe':options}
)


