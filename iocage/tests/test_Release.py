import Release

from hypothesis import given
import hypothesis.strategies as st


class TestRelease(object):

    def valid_release_name():
        from string import ascii_letters
        from string import digits

        alphabet = ascii_letters + digits + '_-.'
        return st.text(alphabet=alphabet, min_size=1, max_size=255)

    @given(name=valid_release_name())
    def test_fetch_release(self, name, host, logger, zfs, root_dataset):
        try:
            release = Release.Release(name=name, host=host, logger=logger, zfs=zfs)
            release.fetch()
        except OSError as err:
            if err.code is 404:
                pass
