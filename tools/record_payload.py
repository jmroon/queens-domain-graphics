"""Record reviewed runtime files after a deliberate release update."""

import hashlib
import json

from package_release import payload
from paths import REPO

files = {
    k: hashlib.sha256(v).hexdigest() for k, v in payload().items() if k.startswith("QueensDomain/")
}
(REPO / "release-files.json").write_text(json.dumps(files, indent=2) + "\n")
print("Updated release-files.json; review its diff before committing.")
