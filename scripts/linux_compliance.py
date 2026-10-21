#!/usr/bin/env python3
"""Licence compliance for the Linux Data Viewer AppImage (runs on the Debian/Ubuntu build runner).

    linux_compliance.py --appimage X.AppImage --version 2.0.0 --arch x64 --out out/dist --work WORK \
                        --notices out/licenses/THIRD_PARTY_NOTICES.txt

What it does
  1. unpacks the AppImage and lists every bundled shared library / helper binary with the distribution
     package it came from (name, version, source package, licence from /usr/share/doc/<pkg>/copyright, sha256);
  2. writes THIRD_PARTY_NOTICES-linux.txt, copies the copyright files and the full common licence texts
     (GPL, LGPL, MPL, Apache, BSD, ...) into the AppImage (usr/share/doc/ddc-data-viewer/ and usr/share/doc/<pkg>/);
  3. downloads the matching distribution source packages (same versions) and packs them into
     ddc-data-viewer-<version>-linux-<arch>-third-party-sources.tar.xz (split when larger than 1.9 GB);
  4. writes SOURCE-OFFER.txt and re-creates the AppImage with the added files (same runtime and compression).
Exit code 1 on any unresolved library, missing source package or a GPL-only (no linking exception) library.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# GPL-only libraries are never bundled (a proprietary application must not ship or link them): they stay a system
# dependency.  libjbig0 (JBIG-KIT) is GPL-2+ without a linking exception.
EXCLUDE_PACKAGES = {'libjbig0'}
# Flagged by the text heuristic but reviewed: the library itself is permissive / LGPL, or dual licensed with a
# permissive or LGPL choice; the GPL part belongs to tools, tests or an optional plugin that is not bundled.
REVIEWED_OK = {
    'libbz2-1.0': 'bzip2 licence (BSD-style)', 'libcap2': 'BSD-3-Clause or GPL-2 (BSD-3-Clause chosen)',
    'libevdev2': 'MIT', 'libglib2.0-0': 'LGPL-2.1+', 'libglib2.0-dev': 'LGPL-2.1+ tools',
    'libicu70': 'ICU licence', 'liblcms2-2': 'MIT (GPL-3 only for the separate fast_float plugin)',
    'liblz4-1': 'BSD-2-Clause (library)', 'libpng16-16': 'libpng licence', 'libsqlite3-0': 'public domain',
    'libzstd1': 'BSD-3-Clause or GPL-2 (BSD-3-Clause chosen)',
}
CONTACT = 'info@datadrivenconstruction.io'
RELEASES = 'https://github.com/datadrivenconstruction/cad2data-Revit-IFC-DWG/releases'


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def out(cmd):
    return subprocess.run(cmd, check=False, text=True, capture_output=True).stdout.strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def is_elf(path):
    try:
        with open(path, 'rb') as f:
            return f.read(4) == b'\x7fELF'
    except OSError:
        return False


def owning_package(path_in_image, digest):
    """(package, exact) of the distribution package that ships this file."""
    base = os.path.basename(path_in_image)
    lines = out(['dpkg', '-S', '*/' + base]).splitlines()
    cands = []
    for line in lines:
        if ': ' not in line:
            continue
        pkgs, fpath = line.split(': ', 1)
        for pkg in pkgs.split(', '):
            cands.append((pkg.split(':')[0], fpath))
    for pkg, fpath in cands:  # byte-identical file on the build machine
        if os.path.isfile(fpath) and sha256(fpath) == digest:
            return pkg, True
    if cands:
        return cands[0][0], False
    return None, False


def package_info(pkg):
    fmt = '${Version}\t${source:Package}\t${source:Version}\t${Architecture}'
    version, src, srcver, arch = out(['dpkg-query', '-W', '-f=' + fmt, pkg]).split('\t')
    return version, src, srcver or version, arch


def licences_of(pkg):
    copyright_path = Path('/usr/share/doc') / pkg / 'copyright'
    if not copyright_path.exists():
        return [], None
    text = copyright_path.read_text(encoding='utf-8', errors='replace')
    names = set()
    for m in re.finditer(r'^License:\s*(.+)$', text, re.M):
        for part in re.split(r'\s+(?:and|or|AND|OR)\s+|,\s*', m.group(1).strip()):
            part = part.strip()
            if part and not part.startswith('/'):
                names.add(part)
    if not names:
        for key in ('LGPL-2.1', 'LGPL-3', 'LGPL-2', 'GPL-3', 'GPL-2', 'MPL-2.0', 'Apache-2.0', 'BSD', 'MIT', 'ISC', 'Zlib',
                    'OFL', 'public domain', 'Expat'):
            if key.lower() in text.lower():
                names.add(key)
    return sorted(names), copyright_path


def gpl_only(names, copyright_text):
    """True when the package carries a GPL licence and no LGPL / linking-exception wording at all."""
    joined = ' '.join(names)
    if not re.search(r'(?<!L)GPL', joined):
        return False
    return not (re.search(r'LGPL', joined) or re.search(r'exception', copyright_text, re.I))


def enable_sources():
    for f in ['/etc/apt/sources.list', *map(str, Path('/etc/apt/sources.list.d').glob('*'))]:
        p = Path(f)
        if not p.is_file():
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        if p.suffix == '.sources':  # deb822
            new = re.sub(r'^Types:\s*deb\s*$', 'Types: deb deb-src', text, flags=re.M)
        else:
            new = re.sub(r'^#\s*(deb-src\s)', r'\1', text, flags=re.M)
        if new != text:
            subprocess.run(['sudo', 'tee', f], input=new, text=True, stdout=subprocess.DEVNULL, check=True)
    run(['sudo', 'apt-get', 'update', '-qq'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--appimage', required=True, type=Path)
    ap.add_argument('--version', required=True)
    ap.add_argument('--arch', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--work', required=True, type=Path)
    ap.add_argument('--notices', required=True, type=Path, help='THIRD_PARTY_NOTICES.txt of the application itself')
    ap.add_argument('--report-only', action='store_true')
    a = ap.parse_args()

    work = a.work
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    a.out.mkdir(parents=True, exist_ok=True)
    image = work / 'app.AppImage'
    shutil.copyfile(a.appimage, image)
    image.chmod(0o755)
    env = dict(os.environ, APPIMAGE_EXTRACT_AND_RUN='1')
    subprocess.run([str(image), '--appimage-extract'], cwd=work, env=env, check=True, stdout=subprocess.DEVNULL)
    root = work / 'squashfs-root'
    offset = int(out([str(image), '--appimage-offset']))

    # 1. what is inside
    rows, problems, packages, excluded = [], [], {}, []
    files = sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and is_elf(p))
    for f in files:
        rel = f.relative_to(root).as_posix()
        if f.name.startswith('ddc-data-viewer') or f.name.startswith('AppRun'):
            continue
        digest = sha256(f)
        pkg, exact = owning_package(rel, digest)
        if pkg is None:
            problems.append('no distribution package for ' + rel)
            continue
        if pkg in EXCLUDE_PACKAGES:
            excluded.append((rel, pkg))
            continue
        rows.append((rel, pkg, exact, digest))
        packages.setdefault(pkg, []).append(rel)

    notes = []
    sources = {}
    gpl_flags = []
    for pkg in sorted(packages):
        version, src, srcver, arch = package_info(pkg)
        names, cpath = licences_of(pkg)
        text = cpath.read_text(encoding='utf-8', errors='replace') if cpath else ''
        if not cpath:
            problems.append('no copyright file for ' + pkg)
        if not names:
            problems.append('no licence found for ' + pkg)
        if pkg not in EXCLUDE_PACKAGES and pkg not in REVIEWED_OK and gpl_only(names, text):
            gpl_flags.append(pkg)
        sources[(src, srcver)] = pkg
        packages[pkg] = (version, src, srcver, names, packages[pkg])
    if gpl_flags:
        problems.append('GPL package without LGPL or exception wording: ' + ', '.join(gpl_flags))

    lines = ['DDC Data Viewer - Linux AppImage (%s): third-party components' % a.arch, '',
             'The AppImage bundles the shared libraries below, unchanged, from the Ubuntu 22.04 packages named here.',
             'Licence texts: usr/share/doc/<package>/copyright and usr/share/doc/ddc-data-viewer/licenses/ (inside the',
             'AppImage). The matching source packages of exactly these versions are published as the release asset',
             'ddc-data-viewer-%s-linux-%s-third-party-sources.tar.xz (see SOURCE-OFFER.txt).' % (a.version, a.arch),
             'To use your own version of a LGPL library see README (Linux): replace the file under usr/lib and re-run.', '',
             'Packages (name, version, source package, licences):']
    for pkg in sorted(packages):
        version, src, srcver, names, rels = packages[pkg]
        lines.append('  %s %s | source: %s %s | %s' % (pkg, version, src, srcver, ', '.join(names) or '?'))
    if excluded:
        lines += ['', 'Not bundled (GPL without a linking exception; install from your distribution if needed):']
        for pkg in sorted({p for _, p in excluded}):
            lines.append('  %s %s' % (pkg, package_info(pkg)[0]))
    lines += ['', 'Reviewed licence notes:']
    for pkg in sorted(packages):
        if pkg in REVIEWED_OK:
            lines.append('  %s: %s' % (pkg, REVIEWED_OK[pkg]))
    lines += ['', 'Files (path inside the AppImage, package, sha256):']
    for rel, pkg, exact, digest in rows:
        lines.append('  %s | %s | %s%s' % (rel, pkg, digest, '' if exact else ' | build-machine copy differs'))
    app_notices = a.notices.read_text(encoding='utf-8', errors='replace') if a.notices.exists() else ''
    notice_text = '\n'.join(lines) + '\n\n' + '=' * 78 + '\nApplication components (Rust crates, web bundle)\n' + '=' * 78 + '\n' + app_notices
    report = a.out / ('THIRD_PARTY_NOTICES-linux-%s.txt' % a.arch)
    report.write_text(notice_text, encoding='utf-8')
    print('libraries: %d files in %d packages, %d source packages' % (len(rows), len(packages), len(sources)))
    for pkg in sorted(packages):
        print('PKG %s %s | %s' % (pkg, packages[pkg][0], ', '.join(packages[pkg][3])))
    for p in problems:
        print('PROBLEM:', p)
    if a.report_only:
        return 1 if problems else 0

    # 2. licence texts into the image; GPL-only libraries are removed
    for rel, _pkg in excluded:
        (root / rel).unlink()
        for link in list(root.rglob('*')):
            if link.is_symlink() and not link.exists():
                link.unlink()
    docdir = root / 'usr/share/doc/ddc-data-viewer'
    (docdir / 'licenses').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(report, docdir / 'THIRD_PARTY_NOTICES-linux.txt')
    for f in Path('/usr/share/common-licenses').iterdir():
        if f.is_file():
            shutil.copyfile(f, docdir / 'licenses' / f.name)
    for pkg in packages:
        src = Path('/usr/share/doc') / pkg / 'copyright'
        if src.exists():
            dst = root / 'usr/share/doc' / pkg
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst / 'copyright')

    # 3. sources
    enable_sources()
    srcdir = work / 'sources'
    srcdir.mkdir()
    for (src, srcver), pkg in sorted(sources.items()):
        r = subprocess.run(['apt-get', 'source', '--download-only', '%s=%s' % (src, srcver)], cwd=srcdir,
                           capture_output=True, text=True)
        if r.returncode != 0:
            problems.append('source package not available: %s %s' % (src, srcver))
    print('sources fetched:', len(list(srcdir.iterdir())), 'files')
    archive = a.out / ('ddc-data-viewer-%s-linux-%s-third-party-sources.tar.xz' % (a.version, a.arch))
    subprocess.run('tar -C "%s" -cf - . | xz -T0 -6 > "%s"' % (srcdir, archive), shell=True, check=True)
    parts = [archive]
    if archive.stat().st_size > 1_900_000_000:
        subprocess.run(['split', '-b', '1900M', '-d', str(archive), str(archive) + '.part'], check=True)
        archive.unlink()
        parts = sorted(a.out.glob(archive.name + '.part*'))
    print('source archive:', [(p.name, p.stat().st_size) for p in parts])
    names = ', '.join(p.name for p in parts)
    offer = ('Source code offer - DDC Data Viewer %s (Linux %s)\n\n'
             'The AppImage contains free software libraries (see THIRD_PARTY_NOTICES-linux-%s.txt) licensed under the GNU\n'
             'LGPL / GPL and other licences. The complete corresponding source packages of exactly the bundled versions\n'
             '(including the build scripts) are published with this release:\n  %s\n  %s\n'
             '%s\n'
             'This source archive is offered for at least three years after the last distribution of the AppImage.\n'
             'If you cannot download it, write to %s and the source will be sent to you on request.\n'
             'The AppImage can be unpacked (./ddc-data-viewer-*.AppImage --appimage-extract); the libraries are in\n'
             'squashfs-root/usr/lib and can be replaced by your own builds (see README).\n'
             % (a.version, a.arch, a.arch, RELEASES, names,
                'To reassemble split parts: cat <name>.part* > <name>' if len(parts) > 1 else '', CONTACT))
    (a.out / 'SOURCE-OFFER.txt').write_text(offer, encoding='utf-8')
    shutil.copyfile(a.out / 'SOURCE-OFFER.txt', docdir / 'SOURCE-OFFER.txt')

    # 4. rebuild the AppImage: same runtime, new squashfs
    info = out(['unsquashfs', '-o', str(offset), '-s', str(image)])
    comp = re.search(r'Compression (\w+)', info).group(1)
    bs = re.search(r'Block size (\d+)', info).group(1)
    sq = work / 'new.squashfs'
    run(['mksquashfs', str(root), str(sq), '-root-owned', '-noappend', '-comp', comp, '-b', bs],
        stdout=subprocess.DEVNULL)
    new = work / 'new.AppImage'
    with open(image, 'rb') as f:
        runtime = f.read(offset)
    new.write_bytes(runtime + sq.read_bytes())
    new.chmod(0o755)
    shutil.copyfile(new, a.appimage)
    for p in problems:
        print('PROBLEM:', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
