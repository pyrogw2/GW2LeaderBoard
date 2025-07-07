# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['workflow_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[
        'requests',
        'beautifulsoup4',
        'bs4',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        'gw2_leaderboard',
        'gw2_leaderboard.utils',
        'gw2_leaderboard.parsers',
        'gw2_leaderboard.core',
        'gw2_leaderboard.web',
        'gw2_leaderboard.web.templates'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='workflow_ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
