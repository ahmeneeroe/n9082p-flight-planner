"""Unit conversion utilities for aviation performance calculations."""


def mph_to_knots(mph: float) -> float:
    return mph * 0.868976

def knots_to_mph(knots: float) -> float:
    return knots / 0.868976

def ft_to_m(ft: float) -> float:
    return ft * 0.3048

def m_to_ft(m: float) -> float:
    return m / 0.3048

def f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9

def c_to_f(c: float) -> float:
    return c * 9 / 5 + 32

def sm_to_nm(sm: float) -> float:
    return sm * 0.868976

def nm_to_sm(nm: float) -> float:
    return nm / 0.868976

def inhg_to_hpa(inhg: float) -> float:
    return inhg * 33.8639

def hpa_to_inhg(hpa: float) -> float:
    return hpa / 33.8639
