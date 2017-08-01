import Release

from hypothesis import given
import hypothesis.strategies as st


class TestRelease(object):

    @given(name=st.text())
    def test_fetch_release(self, name, host, logger, zfs, root_dataset):

        release = Release.Release(name=name, host=host, logger=logger, zfs=zfs)
        release.fetch()
