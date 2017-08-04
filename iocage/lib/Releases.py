import iocage.lib.Release
import iocage.lib.helpers


class Releases:

    def __init__(self, host=None, zfs=None, logger=None):
        iocage.lib.helpers.init_host(self, host)
        self.zfs = zfs

    @property
    def dataset(self):
        return self.host.datasets.releases

    @property
    def local(self):
        release_datasets = self.dataset.children
        return list(map(
            lambda x: iocage.lib.Release.Release(
                name=x.name.split("/").pop(),
                host=self.host,
                zfs=self.zfs
            ),
            release_datasets
        ))

    @property
    def available(self):
        return self.host.distribution.releases

    @property
    def releases_folder(self):
        return self.dataset.mountpoint

    def find_by_name(self, name):
        for release in self.local:
            if release.name == name:
                return release
        raise Exception(f"Release {name} not fetched")
