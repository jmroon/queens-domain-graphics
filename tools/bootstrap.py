"""Download the pinned official build tools, verifying archives and executables."""
import hashlib,io,json,zipfile
from urllib.request import Request,urlopen
from paths import REPO,TOOLS

def digest(data):return hashlib.sha256(data).hexdigest()
def bootstrap():
    for tool in json.loads((REPO/'tools/toolchain.json').read_text()):
        if all((TOOLS/p).is_file() and digest((TOOLS/p).read_bytes())==s['sha256'] for p,s in tool['files'].items()):
            print(tool['name']+': verified');continue
        req=Request(tool['url'],headers={'User-Agent':'QueensDomain-Graphics-build'})
        with urlopen(req,timeout=120) as response:data=response.read()
        if digest(data)!=tool['sha256']:raise RuntimeError('Download hash mismatch: '+tool['name'])
        archive=zipfile.ZipFile(io.BytesIO(data)) if tool['archive'] else None
        try:
            for rel,spec in tool['files'].items():
                contents=archive.read(spec['member']) if archive else data
                if digest(contents)!=spec['sha256']:raise RuntimeError('Executable hash mismatch: '+rel)
                path=TOOLS/rel
                assert path.resolve().is_relative_to(TOOLS.resolve())
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(contents)
        finally:
            if archive:archive.close()
        print(tool['name']+': downloaded and verified')
if __name__=='__main__':bootstrap()
