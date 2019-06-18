import re


version_re = re.compile('(?P<major>\\d+?).(?P<minor>\\d+?)(-r(?P<rev>\\d+))?')


class Version:
    def __init__(self, ver_str):
        """
        >>> Version('1.0-r123')
        Version(1.0-r123)
        >>> Version('1.0')
        Version(1.0-r0)
        """
        match = version_re.match(ver_str)
        major = int(match.group('major'))
        minor = int(match.group('minor'))
        rev = int(match.group('rev')) if match.group('rev') is not None else 0
        self._version = {'major': major, 'minor': minor, 'revision': rev}
        self._normalized = '{}.{}-r{}'.format(self._version['major'], self._version['minor'], self._version['revision'])

    @property
    def major(self):
        """
        >>> Version('2.3').major
        2
        """
        return self._version['major']

    @property
    def minor(self):
        """
        >>> Version('2.3').minor
        3
        """
        return self._version['minor']

    @property
    def revision(self):
        """
        >>> Version('2.3-r45').revision
        45
        """
        return self._version['revision']

    def __le__(self, other):
        """
        >>> Version('1.0-r0') <= Version('1.0-r0')
        True
        >>> Version('1.0-r0') <= Version('1.0-r1')
        True
        >>> Version('1.0-r0') <= Version('1.1-r0')
        True
        >>> Version('1.0-r0') <= Version('2.0-r0')
        True
        >>> Version('1.0-r1') <= Version('1.0-r0')
        False
        >>> Version('1.1-r0') <= Version('1.0-r0')
        False
        >>> Version('2.0-r0') <= Version('1.0-r0')
        False
        """
        return self.compare(other) != 1

    def __eq__(self, other):
        """
        >>> Version('1.0-r0') == Version('1.0-r0')
        True
        >>> Version('1.0-r0') == Version('1.0-r1')
        False
        >>> Version('1.0-r0') == Version('1.1-r0')
        False
        >>> Version('1.0-r0') == Version('2.0-r0')
        False
        """
        return self.compare(other) == 0

    def __ne__(self, other):
        """
        >>> Version('1.0-r0') != Version('1.0-r0')
        False
        >>> Version('1.0-r0') != Version('1.0-r1')
        True
        >>> Version('1.0-r0') != Version('1.1-r0')
        True
        >>> Version('1.0-r0') != Version('2.0-r0')
        True
        """
        return self.compare(other) != 0

    def __lt__(self, other):
        """
        >>> Version('1.0-r0') < Version('1.0-r0')
        False
        >>> Version('1.0-r0') < Version('1.0-r1')
        True
        >>> Version('1.0-r0') < Version('1.1-r0')
        True
        >>> Version('1.0-r0') < Version('2.0-r0')
        True
        >>> Version('1.0-r1') < Version('1.0-r0')
        False
        >>> Version('1.1-r0') < Version('1.0-r0')
        False
        >>> Version('2.0-r0') < Version('1.0-r0')
        False
        """
        return self.compare(other) == -1

    def __gt__(self, other):
        """
        >>> Version('1.0-r0') > Version('1.0-r0')
        False
        >>> Version('1.0-r0') > Version('1.0-r1')
        False
        >>> Version('1.0-r0') > Version('1.1-r0')
        False
        >>> Version('1.0-r0') > Version('2.0-r0')
        False
        >>> Version('1.0-r1') > Version('1.0-r0')
        True
        >>> Version('1.1-r0') > Version('1.0-r0')
        True
        >>> Version('2.0-r0') > Version('1.0-r0')
        True
        """
        return self.compare(other) == 1

    def __ge__(self, other):
        """
        >>> Version('1.0-r0') >= Version('1.0-r0')
        True
        >>> Version('1.0-r0') >= Version('1.0-r1')
        False
        >>> Version('1.0-r0') >= Version('1.1-r0')
        False
        >>> Version('1.0-r0') >= Version('2.0-r0')
        False
        >>> Version('1.0-r1') >= Version('1.0-r0')
        True
        >>> Version('1.1-r0') >= Version('1.0-r0')
        True
        >>> Version('2.0-r0') >= Version('1.0-r0')
        True
        """
        return self.compare(other) != -1

    # noinspection PyProtectedMember
    def compare(self, other):
        """
        >>> Version('1.0-r0').compare(Version('1.0-r0'))
        0
        >>> Version('1.0-r1').compare(Version('1.0-r0'))
        1
        >>> Version('1.0-r0').compare(Version('1.0-r1'))
        -1
        """
        if self._version['major'] == other._version['major']:
            if self._version['minor'] == other._version['minor']:
                if self._version['revision'] == other._version['revision']:
                    return 0
                else:
                    return -1 if self._version['revision'] < other._version['revision'] else 1
            else:
                return -1 if self._version['minor'] < other._version['minor'] else 1
        else:
            return -1 if self._version['major'] < other._version['major'] else 1

    def __str__(self) -> str:
        """
        >>> str(Version('1.0'))
        '1.0-r0'
        """
        return self._normalized

    def __repr__(self):
        return 'Version({})'.format(self._normalized)

    def __hash__(self) -> int:
        return self._normalized.__hash__()
