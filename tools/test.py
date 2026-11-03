"""Run control/menu regression tests and verify the release payload."""
import subprocess,sys
from paths import REPO
for name in ('test_presets.py','test_menu.py'):
    subprocess.run([sys.executable,str(REPO/'tests'/name)],check=True)
from package_release import package
package()
subprocess.run([sys.executable,str(REPO/'tests/test_package.py')],check=True)
