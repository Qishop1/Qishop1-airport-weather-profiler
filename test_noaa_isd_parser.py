from wxprofiler.sources.noaa_isd import parse_isd_line
from wxprofiler.parsing.normalize import normalize_noaa_isd


def build_line() -> str:
    chars = list(' ' * 140)
    def put(start: int, text: str) -> None:
        chars[start:start+len(text)] = list(text)
    put(0, '0135')
    put(4, '474340')
    put(10, '99999')
    put(15, '20260101')
    put(23, '1200')
    put(28, '+42800')
    put(34, '+141666')
    put(41, 'FM-15')
    put(46, '+0025')
    put(51, 'RJCC ')
    put(56, 'V020')
    put(60, '330')
    put(63, '1')
    put(64, 'N')
    put(65, '0050')
    put(69, '1')
    put(70, '00300')
    put(75, '1')
    put(76, '9')
    put(77, 'N')
    put(78, '005000')
    put(84, '1')
    put(85, '9')
    put(86, '1')
    put(87, '-0050')
    put(92, '1')
    put(93, '-0080')
    put(98, '1')
    put(99, '10132')
    put(104, '1')
    put(105, 'MW170AA1010010')
    return ''.join(chars)


def test_parse_isd_line():
    row = parse_isd_line(build_line())
    assert row is not None
    assert row['station'] == 'RJCC'
    assert row['wind_dir_deg'] == 330.0
    assert round(row['wind_speed_kt'], 2) == 9.72
    assert row['visibility_m'] == 5000.0
    assert round(row['ceiling_ft']) == 984
    assert row['temperature_c'] == -5.0
    assert row['dewpoint_c'] == -8.0
    assert row['altimeter_hpa'] == 1013.2
    assert 'SN' in row['wx_tokens']


def test_normalize_noaa_isd():
    row = parse_isd_line(build_line())
    obs = normalize_noaa_isd(row, 'RJCC', 'Asia/Tokyo')
    assert obs.station == 'RJCC'
    assert obs.valid_local.hour == 21
    assert obs.ceiling_ft is not None
    assert 'SN' in obs.wx_tokens


if __name__ == '__main__':
    test_parse_isd_line()
    test_normalize_noaa_isd()
    print('NOAA ISD parser smoke test passed')
