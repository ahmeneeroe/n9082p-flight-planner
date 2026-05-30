"""N9082P Performance Calculator -- Main Interface

EXPERIMENTAL -- Digitized approximation of POH Section 5 charts.
Not validated against real-world flight data.
Supplements but does NOT replace the POH.

Usage:
    from src.calculator import N9082P

    perf = N9082P()

    # Takeoff at Walla Walla (S95), elev 1194 ft
    print(perf.takeoff(pressure_alt_ft=1200, oat_f=75, weight_lb=2800, headwind_kt=5))

    # Cruise at 7500 ft, 65% power
    print(perf.cruise(pressure_alt_ft=7500, oat_f=30, percent_power=65))

    # Landing at S95
    print(perf.landing(pressure_alt_ft=1200, oat_f=75, weight_lb=2600, headwind_kt=8))
"""

from .models import power_settings, stall_speed, takeoff, landing
from .models import fuel_consumption, climb, airspeed_cal, cruise
from .utils.atmosphere import density_altitude, standard_temp_f
from .utils.units import mph_to_knots


class N9082P:
    """Performance calculator for N9082P PA-24-260B Comanche.

    All methods return dictionaries with clearly labeled values.
    Primary units are knots/feet/pounds/gallons.
    MPH values included where the POH uses MPH natively.
    """

    # Aircraft constants
    MAX_GROSS_WEIGHT = 3100  # lb
    MAX_LANDING_WEIGHT = 2945  # lb
    BASIC_FUEL_GAL = 56  # basic (inboard) fuel
    TOTAL_FUEL_GAL = 86  # basic + reserve (outboard)
    EMPTY_WEIGHT = 1910.65  # lb (N9082P specific)
    USEFUL_LOAD = 1189.35  # lb

    def takeoff(self, pressure_alt_ft: float, oat_f: float,
                weight_lb: float = 3100.0,
                headwind_kt: float = 0.0,
                surface: str = "paved_dry",
                uphill_deg: float = 0.0) -> dict:
        """Compute takeoff performance.

        Returns ground run and 50-ft obstacle distance.
        POH Figures 5-06 and 5-07. Short-field technique (15-deg flaps).
        """
        da = density_altitude(pressure_alt_ft, oat_f)

        ground_run = takeoff.takeoff_ground_run(
            pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface, uphill_deg)
        over_50 = takeoff.takeoff_over_50ft(
            pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface, uphill_deg)

        vs = stall_speed.stall_speed_knots(weight_lb, "full_flaps_gear_down")

        return {
            "density_altitude_ft": round(da),
            "ground_run_ft": ground_run,
            "over_50ft_obstacle_ft": over_50,
            "ground_run_standard_ft": ground_run * 2,  # non-short-field
            "vso_kt": vs,
            "conditions": {
                "pressure_alt_ft": pressure_alt_ft,
                "oat_f": oat_f,
                "weight_lb": weight_lb,
                "headwind_kt": headwind_kt,
                "surface": surface,
                "technique": "short_field_15_flaps",
            },
            "warning": "Short-field technique. Standard takeoff ≈ 2x ground run.",
        }

    def landing(self, pressure_alt_ft: float, oat_f: float,
                weight_lb: float = 2945.0,
                headwind_kt: float = 0.0,
                surface: str = "paved_dry",
                downhill_deg: float = 0.0) -> dict:
        """Compute landing performance.

        Returns ground roll and 50-ft obstacle distance.
        POH Figures 5-13 and 5-14. Short-field (32-deg flaps, max braking).
        """
        da = density_altitude(pressure_alt_ft, oat_f)

        ground_roll = landing.landing_ground_roll(
            pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface, downhill_deg)
        over_50 = landing.landing_over_50ft(
            pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface, downhill_deg)

        v_app = stall_speed.approach_speed_knots(weight_lb, "full_flaps_gear_down")

        return {
            "density_altitude_ft": round(da),
            "ground_roll_ft": ground_roll,
            "over_50ft_obstacle_ft": over_50,
            "ground_roll_standard_ft": ground_roll * 2,  # non-short-field
            "approach_speed_kt": v_app,
            "conditions": {
                "pressure_alt_ft": pressure_alt_ft,
                "oat_f": oat_f,
                "weight_lb": weight_lb,
                "headwind_kt": headwind_kt,
                "surface": surface,
                "technique": "short_field_32_flaps_max_braking",
            },
            "warning": "Short-field technique. Standard landing ≈ 2x ground roll.",
        }

    def climb(self, pressure_alt_ft: float, oat_f: float,
              target_alt_ft: float = None,
              config: str = "clean",
              weight_lb: float = 3100.0) -> dict:
        """Compute climb performance.

        POH Figures 5-08 and 5-09.
        """
        da = density_altitude(pressure_alt_ft, oat_f)
        roc = climb.rate_of_climb(pressure_alt_ft, oat_f, config, weight_lb)
        vx = climb.vx_knots(pressure_alt_ft, oat_f, config)
        vy = climb.vy_knots(pressure_alt_ft, oat_f, config)

        result = {
            "density_altitude_ft": round(da),
            "rate_of_climb_fpm": roc,
            "vx_kt": vx,
            "vy_kt": vy,
            "vx_mph": climb.vx_mph(pressure_alt_ft, oat_f, config),
            "vy_mph": climb.vy_mph(pressure_alt_ft, oat_f, config),
            "fuel_flow_climb_gph": fuel_consumption.fuel_flow_climb(),
        }

        if target_alt_ft is not None:
            ttc = climb.time_to_climb(pressure_alt_ft, target_alt_ft, oat_f, config, weight_lb)
            result["time_to_climb_min"] = ttc
            result["fuel_to_climb_gal"] = round(ttc * fuel_consumption.fuel_flow_climb() / 60.0, 1)

        return result

    def cruise(self, pressure_alt_ft: float, oat_f: float,
               percent_power: float = 65.0,
               rpm: int = 2400,
               mixture: str = "best_economy",
               fuel_gal: float = 86.0) -> dict:
        """Compute cruise performance.

        POH Figures 5-04, 5-10, 5-15.
        """
        da = density_altitude(pressure_alt_ft, oat_f)

        # Power setting
        map_req = None
        pwr_int = round(percent_power)
        if pwr_int in [55, 65, 75]:
            map_req = power_settings.get_map_required(
                pressure_alt_ft, rpm, pwr_int, oat_f)

        # Fuel flow
        ff = fuel_consumption.fuel_flow_from_percent(percent_power, rpm, mixture)

        # True airspeed
        tas_kt = cruise.true_airspeed_knots(pressure_alt_ft, oat_f, percent_power)
        tas_mph = cruise.true_airspeed_mph(pressure_alt_ft, oat_f, percent_power)

        # Range and endurance
        rng = cruise.range_nm(percent_power, fuel_gal)
        endur = cruise.endurance_hrs(percent_power)

        return {
            "density_altitude_ft": round(da),
            "map_required_inhg": map_req,
            "fuel_flow_gph": ff,
            "tas_kt": tas_kt,
            "tas_mph": tas_mph,
            "range_nm": rng,
            "endurance_hrs": endur,
            "conditions": {
                "pressure_alt_ft": pressure_alt_ft,
                "oat_f": oat_f,
                "percent_power": percent_power,
                "rpm": rpm,
                "mixture": mixture,
                "fuel_gal": fuel_gal,
            },
        }

    def stall(self, weight_lb: float = 3100.0) -> dict:
        """Compute stall speeds at various configurations.

        POH Figure 5-05.
        """
        return {
            "weight_lb": weight_lb,
            "clean_kt": stall_speed.stall_speed_knots(weight_lb, "clean"),
            "clean_mph": round(stall_speed.stall_speed_mph(weight_lb, "clean"), 1),
            "flaps_15_gear_down_kt": stall_speed.stall_speed_knots(weight_lb, "flaps_15_gear_down"),
            "full_flaps_gear_down_kt": stall_speed.stall_speed_knots(weight_lb, "full_flaps_gear_down"),
            "full_flaps_gear_down_mph": round(stall_speed.stall_speed_mph(weight_lb, "full_flaps_gear_down"), 1),
            "approach_speed_kt": stall_speed.approach_speed_knots(weight_lb),
        }

    def power_setting(self, pressure_alt_ft: float, rpm: int,
                      percent_power: int, oat_f: float = None) -> dict:
        """Look up required manifold pressure.

        POH Figure 5-15.
        """
        map_req = power_settings.get_map_required(
            pressure_alt_ft, rpm, percent_power, oat_f)

        mixture_econ = power_settings.get_fuel_flow(percent_power, "best_economy")
        mixture_power = power_settings.get_fuel_flow(percent_power, "best_power")

        return {
            "map_required_inhg": map_req,
            "fuel_flow_best_economy_gph": mixture_econ,
            "fuel_flow_best_power_gph": mixture_power,
            "available": map_req is not None,
            "note": "Power not available at this altitude/RPM" if map_req is None else None,
        }

    def summary(self, pressure_alt_ft: float, oat_f: float,
                weight_lb: float = 3100.0,
                headwind_kt: float = 0.0,
                cruise_alt_ft: float = None,
                cruise_power: float = 65.0,
                fuel_gal: float = 86.0) -> dict:
        """Complete flight performance summary.

        Computes takeoff, climb, cruise, and landing performance
        for a given set of conditions.
        """
        cruise_alt = cruise_alt_ft or pressure_alt_ft + 5000
        cruise_oat = standard_temp_f(cruise_alt)

        # Estimate landing weight (subtract climb + cruise fuel estimate)
        climb_info = self.climb(pressure_alt_ft, oat_f, target_alt_ft=cruise_alt)
        fuel_climb = climb_info.get("fuel_to_climb_gal", 2.0)
        landing_weight = min(weight_lb - fuel_climb * 6.0, self.MAX_LANDING_WEIGHT)

        return {
            "takeoff": self.takeoff(pressure_alt_ft, oat_f, weight_lb, headwind_kt),
            "climb": climb_info,
            "cruise": self.cruise(cruise_alt, cruise_oat, cruise_power, fuel_gal=fuel_gal),
            "stall": self.stall(weight_lb),
            "landing_estimate": self.landing(pressure_alt_ft, oat_f,
                                             min(landing_weight, self.MAX_LANDING_WEIGHT),
                                             headwind_kt),
        }
