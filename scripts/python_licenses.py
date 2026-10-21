#!/usr/bin/env python3
"""Licence files for a Nuitka standalone folder (called by the products' build_cli.py through DDC_LICENSE_HOOK).

    python_licenses.py <dist-folder>

Writes <dist-folder>/licenses/: the upstream licence texts (verbatim, see legal/LICENSE_AUDIT_2026-10.csv) of the
components compiled into or bundled with the CPython runtime, and on Debian/Ubuntu the copyright file of the
distribution package of every bundled shared library plus the GPL/LGPL texts when a package needs them.
The texts are pinned to the exact interpreter version; another interpreter fails the build so that the texts are
refreshed from upstream instead of silently going stale.
"""
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE.parent / 'legal' / 'licenses'
OS = 'linux' if sys.platform.startswith('linux') else 'darwin' if sys.platform == 'darwin' else sys.platform
PINNED_PYTHON = {'linux': '3.13.16', 'darwin': '3.13.15'}
BY_FILE = [  # (file name pattern, {os: [texts]})
    (r'^(_hashlib|_ssl)\b|libcrypto|libssl', {'linux': ['OpenSSL-3.0.2-LICENSE.txt'], 'darwin': ['OpenSSL-3.0.21-LICENSE.txt']}),
    (r'^_ctypes\b|libffi', {'linux': ['libffi-3.4.2-LICENSE.txt']}),  # macOS links the system libffi (not shipped)
    (r'^(pyexpat|_elementtree)\b|libexpat', {'darwin': ['expat-COPYING-from-cpython-3.13.txt']}),  # Linux build uses no expat
    (r'^_decimal\b|libmpdec', {'linux': ['mpdecimal-2.5.1-LICENSE.txt'], 'darwin': ['mpdecimal-2.5.1-LICENSE.txt']}),
    (r'^(_md5|_sha1|_sha2|_sha3|_blake2)\b', {'linux': ['hacl-star-bb3d0dc8-LICENSE.txt', 'hacl-MIT-header-from-cpython-3.13.txt'],
                                              'darwin': ['hacl-star-bb3d0dc8-LICENSE.txt', 'hacl-MIT-header-from-cpython-3.13.txt']}),
]


def is_native(p):
    return re.search(r'\.(so(\.\d+)*|dylib|pyd)$', p.name) is not None


def out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    want = PINNED_PYTHON.get(OS)
    if want and platform.python_version() != want:
        sys.exit('licence texts are pinned to Python %s on %s, this is %s: refresh legal/licenses from upstream'
                 % (want, OS, platform.python_version()))
    dist = Path(sys.argv[1])
    lic = dist / 'licenses'
    lic.mkdir(exist_ok=True)
    natives = sorted(p for p in dist.rglob('*') if p.is_file() and is_native(p))
    texts = set()
    for p in natives:
        for pattern, per_os in BY_FILE:
            if re.search(pattern, p.name):
                texts.update(per_os.get(OS, []))
    for name in sorted(texts):
        shutil.copyfile(TEXTS / name, lic / name)
    lines = ['Licence texts of components compiled into or bundled with the CPython runtime (verbatim from upstream):']
    lines += ['  ' + n for n in sorted(texts)]
    lines += ['', 'CPython itself: PYTHON-LICENSE.txt in the folder above this one.']
    if OS == 'linux' and shutil.which('dpkg'):
        pkgs = {}
        for p in natives:
            if not re.match(r'^lib.*\.so(\.\d+)+$', p.name):
                continue  # extension modules of the interpreter are not distribution packages
            for line in out(['dpkg', '-S', '*/' + p.name]).splitlines():
                if ': ' in line:
                    for pkg in line.split(': ', 1)[0].split(', '):
                        pkgs.setdefault(pkg.split(':')[0], []).append(p.name)
                    break
        lines += ['', 'Distribution packages the shared libraries were taken from (copyright files in this folder):']
        needs_common = set()
        for pkg, files in sorted(pkgs.items()):
            ver = out(['dpkg-query', '-W', '-f=${Version}', pkg])
            cp = Path('/usr/share/doc') / pkg / 'copyright'
            if cp.exists():
                shutil.copyfile(cp, lic / ('copyright-%s.txt' % pkg))
                body = cp.read_text(encoding='utf-8', errors='replace')
                for key in ('GPL-3', 'GPL-2', 'LGPL-2.1', 'LGPL-3', 'LGPL-2', 'MPL-2.0', 'Apache-2.0', 'BSD'):
                    if key in body:
                        needs_common.add(key)
            if pkg == 'libssl3' and not ver.startswith('3.0.2'):
                sys.exit('libssl3 %s: the pinned OpenSSL 3.0.2 licence text must be refreshed' % ver)
            lines.append('  %s %s: %s' % (pkg, ver, ', '.join(sorted(set(files)))))
        common = Path('/usr/share/common-licenses')
        for key in sorted(needs_common):
            f = common / key
            if f.is_file():
                shutil.copyfile(f, lic / ('common-' + key + '.txt'))
        lines += ['', 'The libraries are used unchanged; the licence of each is given in its copyright file.']
    (lic / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('licence files:', len(list(lic.iterdir())))


if __name__ == '__main__':
    main()
