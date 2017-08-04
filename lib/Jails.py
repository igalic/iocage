import Jail
import helpers

import libzfs

class Jails:

  def __init__(self, root_dataset_name="zroot/iocage", host=None, logger=None, zfs=None):
    helpers.init_logger(self, logger)
    helpers.init_zfs(self, zfs)
    helpers.init_host(self, host)
    self.root_dataset_name = "zroot/iocage"
    self.zfs = libzfs.ZFS(history=True, history_prefix="<iocage>")

  def list(self):
    jails = self._get_existing_jails()
    return jails

  def _get_existing_jails(self):
    jails_dataset = self.zfs.get_dataset(f"{self.root_dataset_name}/jails")
    jail_datasets = list(jails_dataset.children)

    return list(map(
      lambda x: Jail.Jail({
        "uuid": x.name.split("/").pop()
      }, logger=self.logger, host=self.host, zfs=self.zfs),
      jail_datasets
    ))
