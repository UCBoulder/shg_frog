from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Collect all plugin modules
hiddenimports = collect_submodules('imageio.plugins') + collect_submodules('imageio.v3_plugins')

# Ensure version metadata exists
datas = copy_metadata('imageio')
