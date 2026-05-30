"""Validation tests for N9082P performance calculator.

Compares computed values against known POH reference values and the
flight planning example in POH Section 5, pages 5-2 through 5-4.

IMPORTANT: These tests validate the digitization accuracy, not
real-world performance. All data is per the POH charts.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.calculator import N9082P
from src.models import power_settings, stall_speed, takeoff, landing
from src.models import fuel_consumption, climb, cruise
from src.utils.atmosphere import density_altitude, standard_temp_f
from src.utils.units import mph_to_knots


def test_power_setting_table():
    """Validate Power Setting Table (Figure 5-15) against POH values."""
    print("=== Power Setting Table (Fig 5-15) ===")

    # Known values from POH at 2400 RPM
    tests = [
        # (alt, rpm, power%, expected_MAP)
        (0,    2400, 55, 19.8),
        (0,    2400, 65, 22.2),
        (0,    2400, 75, 24.8),
        (2000, 2400, 55, 19.4),
        (2000, 2400, 65, 21.8),
        (4000, 2400, 55, 19.0),
        (5000, 2400, 65, 21.1),
        (7000, 2400, 55, 18.4),
        (10000, 2400, 55, 17.7),
        (10000, 2400, 65, 20.0),
        # Other RPM values
        (0, 2100, 55, 22.3),
        (0, 2200, 65, 24.1),
        (0, 2300, 75, 25.8),
        (0, 2500, 75, 24.0),
    ]

    for alt, rpm, pwr, expected in tests:
        result = power_settings.get_map_required(alt, rpm, pwr)
        diff = abs(result - expected) if result else float('inf')
        status = "PASS" if diff < 0.2 else "FAIL"
        print(f"  {status}: {alt}ft/{rpm}RPM/{pwr}% -> {result} inHg (expected {expected}, diff {diff:.1f})")


def test_stall_speeds():
    """Validate stall speeds (Figure 5-05) against POH values."""
    print("\n=== Stall Speed (Fig 5-05) ===")

    # Known values from POH Section 2
    tests = [
        # (weight, config, expected_kt)
        (3100, "clean", 65),
        (3100, "full_flaps_gear_down", 58),
    ]

    for weight, config, expected_kt in tests:
        result = stall_speed.stall_speed_knots(weight, config)
        diff = abs(result - expected_kt)
        status = "PASS" if diff < 2 else "FAIL"
        print(f"  {status}: {weight}lb {config} -> {result} kt (expected {expected_kt}, diff {diff:.1f})")


def test_takeoff_reference():
    """Validate takeoff distances against known POH values."""
    print("\n=== Takeoff Distance (Figs 5-06, 5-07) ===")

    # SL, standard, gross weight, no wind
    # Note: model includes 5% conservative bias, so values will be above POH reference
    gr = takeoff.takeoff_ground_run(0, 59, 3100, 0)
    print(f"  SL/Std/3100/no wind:")
    print(f"    Ground run: {gr} ft (POH: 1260, +5% conservative bias)")
    print(f"    {'PASS' if 1260 <= gr <= 1260*1.12 else 'FAIL'} ground run (within 0-12% conservative)")
    ov = takeoff.takeoff_over_50ft(0, 59, 3100, 0)
    print(f"    Over 50ft:  {ov} ft (POH: 1725, +5% conservative bias)")
    print(f"    {'PASS' if 1725 <= ov <= 1725*1.15 else 'FAIL'} over 50ft (within 0-15% conservative)")

    # POH flight planning example: 2000 ft PA, 60F, 3000 lb, 10 kt headwind
    gr2 = takeoff.takeoff_ground_run(2000, 60, 3000, 10)
    print(f"\n  POH Example (2000ft/60F/3000lb/10kt HW):")
    print(f"    Ground run: {gr2} ft (expected ~1100)")
    ov2 = takeoff.takeoff_over_50ft(2000, 60, 3000, 10)
    print(f"    {'PASS' if abs(gr2 - 1100) < 150 else 'FAIL'} ground run")
    print(f"    Over 50ft:  {ov2} ft (expected ~1500)")
    print(f"    {'PASS' if abs(ov2 - 1500) < 200 else 'FAIL'} over 50ft")


def test_landing_reference():
    """Validate landing distances against known POH values."""
    print("\n=== Landing Distance (Figs 5-13, 5-14) ===")

    # SL, standard, max landing weight, no wind
    gr = landing.landing_ground_roll(0, 59, 2945, 0)
    ov = landing.landing_over_50ft(0, 59, 2945, 0)
    print(f"  SL/Std/2945/no wind:")
    print(f"    Ground roll: {gr} ft (POH: 925, +5% conservative bias)")
    print(f"    Over 50ft:   {ov} ft (POH: 1435, +5% conservative bias)")
    print(f"    {'PASS' if 925 <= gr <= 925*1.12 else 'FAIL'} ground roll (within 0-12% conservative)")
    print(f"    {'PASS' if 1435 <= ov <= 1435*1.12 else 'FAIL'} over 50ft (within 0-12% conservative)")

    # POH example: 4000 ft PA, 60F, 2796 lb, 10 kt headwind
    gr2 = landing.landing_ground_roll(4000, 60, 2796, 10)
    ov2 = landing.landing_over_50ft(4000, 60, 2796, 10)
    print(f"\n  POH Example (4000ft/60F/2796lb/10kt HW):")
    print(f"    Ground roll: {gr2} ft (expected ~850)")
    print(f"    Over 50ft:   {ov2} ft (expected ~1300)")
    print(f"    {'PASS' if abs(gr2 - 850) < 150 else 'FAIL'} ground roll")
    print(f"    {'PASS' if abs(ov2 - 1300) < 200 else 'FAIL'} over 50ft")


def test_climb():
    """Validate climb performance (Figures 5-08, 5-09)."""
    print("\n=== Rate of Climb (Fig 5-08) ===")

    roc_sl = climb.rate_of_climb(0, 59, "clean")
    print(f"  SL, clean: {roc_sl} fpm (expected 1370)")
    print(f"    {'PASS' if abs(roc_sl - 1370) < 50 else 'FAIL'}")

    # VX/VY at sea level
    vx = climb.vx_knots(0, 59, "clean")
    vy = climb.vy_knots(0, 59, "clean")
    print(f"\n=== VX/VY (Fig 5-09) ===")
    print(f"  SL clean: VX={vx} kt, VY={vy} kt")

    # POH example: avg ROC for climb from 2000 to 7000
    ttc = climb.time_to_climb(2000, 7000)
    print(f"\n  Time to climb 2000->7000 ft: {ttc} min (expected ~4.5)")
    print(f"    {'PASS' if abs(ttc - 4.5) < 1.5 else 'FAIL'}")


def test_fuel_consumption():
    """Validate fuel consumption (Figure 5-03)."""
    print("\n=== Fuel Consumption (Fig 5-03) ===")

    tests = [
        (55, "best_economy", 11.4),
        (55, "best_power", 13.5),
        (65, "best_economy", 12.7),
        (65, "best_power", 15.0),
        (75, "best_economy", 14.1),
        (75, "best_power", 16.5),
    ]

    for pwr, mix, expected in tests:
        result = fuel_consumption.fuel_flow_from_percent(pwr, 2400, mix)
        diff = abs(result - expected)
        status = "PASS" if diff < 0.5 else "FAIL"
        print(f"  {status}: {pwr}% {mix} -> {result} GPH (expected {expected})")


def test_cruise_performance():
    """Validate cruise performance (Figures 5-10, 5-15)."""
    print("\n=== Cruise TAS (Fig 5-10) ===")

    # Known values from POH
    tests = [
        # (alt, temp, power%, expected_kt)
        (7000, 34, 75, 158),  # 75% at 7000 ft
    ]

    for alt, temp, pwr, expected_kt in tests:
        result = cruise.true_airspeed_knots(alt, temp, pwr)
        diff = abs(result - expected_kt) if result else float('inf')
        status = "PASS" if diff < 5 else "FAIL"
        print(f"  {status}: {alt}ft/{pwr}% -> {result} kt (expected {expected_kt})")


def test_density_altitude():
    """Validate density altitude calculation."""
    print("\n=== Density Altitude ===")

    # Standard day at SL = 0 ft DA
    da = density_altitude(0, 59)
    print(f"  SL, std (59F): DA = {da:.0f} ft (expected 0)")
    print(f"    {'PASS' if abs(da) < 50 else 'FAIL'}")

    # Hot day at 5000 ft
    da2 = density_altitude(5000, 90)
    print(f"  5000ft, 90F: DA = {da2:.0f} ft (expected ~7880)")
    print(f"    {'PASS' if abs(da2 - 7880) < 200 else 'FAIL'}")


def test_poh_flight_example():
    """Validate against the complete POH flight planning example (Sec 5 p5-2)."""
    print("\n" + "=" * 60)
    print("POH FLIGHT PLANNING EXAMPLE VALIDATION")
    print("=" * 60)

    perf = N9082P()

    print("\n--- Takeoff (2000ft PA, 60F, 3000lb, 10kt HW) ---")
    to = perf.takeoff(2000, 60, 3000, 10)
    print(f"  Ground run:    {to['ground_run_ft']} ft (expected ~1100)")
    print(f"  Over 50ft:     {to['over_50ft_obstacle_ft']} ft (expected ~1500)")

    print("\n--- Climb to 7000 ft ---")
    cl = perf.climb(2000, 60, target_alt_ft=7000)
    print(f"  Rate of climb: {cl['rate_of_climb_fpm']} fpm")
    print(f"  Time to climb: {cl.get('time_to_climb_min', 'N/A')} min (expected ~4.5)")
    print(f"  Fuel to climb: {cl.get('fuel_to_climb_gal', 'N/A')} gal (expected ~1.6)")

    print("\n--- Cruise at 7000 ft, 75% power ---")
    cr = perf.cruise(7000, 34, 75, 2400, "best_economy")
    print(f"  TAS:           {cr['tas_kt']} kt (expected 158)")
    print(f"  TAS:           {cr['tas_mph']} MPH (expected 182)")
    print(f"  MAP required:  {cr['map_required_inhg']} inHg")
    print(f"  Fuel flow:     {cr['fuel_flow_gph']} GPH (expected 14.1 econ)")

    print("\n--- Landing (4000ft PA, 60F, 2796lb, 10kt HW) ---")
    ld = perf.landing(4000, 60, 2796, 10)
    print(f"  Ground roll:   {ld['ground_roll_ft']} ft (expected ~850)")
    print(f"  Over 50ft:     {ld['over_50ft_obstacle_ft']} ft (expected ~1300)")


def test_walla_walla():
    """Performance at home base -- Walla Walla (S95), elev 1194 ft."""
    print("\n" + "=" * 60)
    print("WALLA WALLA (S95) SAMPLE -- Elev 1194 ft")
    print("=" * 60)

    perf = N9082P()

    # Summer day: 90F, light wind
    print("\n--- Summer Day (90F, 5kt HW, 2800 lb) ---")
    to = perf.takeoff(1200, 90, 2800, 5)
    print(f"  DA:            {to['density_altitude_ft']} ft")
    print(f"  Ground run:    {to['ground_run_ft']} ft (short field)")
    print(f"  Over 50ft:     {to['over_50ft_obstacle_ft']} ft")
    print(f"  Standard TO:   ~{to['ground_run_standard_ft']} ft")

    ld = perf.landing(1200, 90, 2700, 5)
    print(f"  Landing roll:  {ld['ground_roll_ft']} ft (short field)")
    print(f"  Landing 50ft:  {ld['over_50ft_obstacle_ft']} ft")
    print(f"  Approach:      {ld['approach_speed_kt']} kt")

    # Winter day: 35F, calm
    print("\n--- Winter Day (35F, calm, 2600 lb) ---")
    to = perf.takeoff(1200, 35, 2600, 0)
    print(f"  DA:            {to['density_altitude_ft']} ft")
    print(f"  Ground run:    {to['ground_run_ft']} ft (short field)")
    print(f"  Over 50ft:     {to['over_50ft_obstacle_ft']} ft")


if __name__ == "__main__":
    test_density_altitude()
    test_power_setting_table()
    test_stall_speeds()
    test_fuel_consumption()
    test_takeoff_reference()
    test_landing_reference()
    test_climb()
    test_cruise_performance()
    test_poh_flight_example()
    test_walla_walla()

    print("\n" + "=" * 60)
    print("All validation tests complete.")
    print("Review results above for PASS/FAIL status.")
    print("=" * 60)
