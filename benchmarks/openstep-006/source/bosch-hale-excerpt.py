# Extracted from UKAEA PROCESS 2f2d82125fab1b0a22ec1bc5891a9f032bc86319
# process/models/physics/fusion_reactions.py; MIT; see PROCESS-LICENSE.
REACTION_CONSTANTS_DT = {
    "bg": 34.3827,
    "mrc2": 1.124656e6,
    "cc1": 1.17302e-9,
    "cc2": 1.51361e-2,
    "cc3": 7.51886e-2,
    "cc4": 4.60643e-3,
    "cc5": 1.35000e-2,
    "cc6": -1.06750e-4,
    "cc7": 1.36600e-5,
}

def bosch_hale_reactivity(
    ion_temperature_profile: np.ndarray, reaction_constants: BoschHaleConstants
) -> np.ndarray:
    """Calculate the velocity-space average reactivity 〈σv〉 [m³/s] for one of four
    nuclear reactions using the Bosch-Hale parametrization.

    The valid range of the fit is 0.2 keV < t < 100 keV except for D-3He where it is
    0.5 keV < t < 190 keV.

    Reactions:
        1. D-T reaction
        2. D-3He reaction
        3. D-D 1st reaction
        4. D-D 2nd reaction

    Parameters
    ----------
    ion_temperature_profile :
        Plasma ion temperature profile in keV.
    reaction_constants :
        Bosch-Hale reaction constants.

    Returns
    -------
    :
        np.ndarray: Velocity-space average reactivity 〈σv〉 [m³/s] for each point in
        the ion temperature profile.

    References
    ----------
    [1] H.-S. Bosch and G. M. Hale, “Improved formulas for fusion cross-sections and
    thermal reactivities,” Nuclear Fusion, vol. 32, no. 4, pp. 611-631, Apr. 1992,
    doi: https://doi.org/10.1088/0029-5515/32/4/i07.
    """  # noqa: RUF002
    theta1 = (
        ion_temperature_profile
        * (
            reaction_constants.cc2
            + ion_temperature_profile
            * (reaction_constants.cc4 + ion_temperature_profile * reaction_constants.cc6)
        )
        / (
            1.0
            + ion_temperature_profile
            * (
                reaction_constants.cc3
                + ion_temperature_profile
                * (
                    reaction_constants.cc5
                    + ion_temperature_profile * reaction_constants.cc7
                )
            )
        )
    )
    theta = ion_temperature_profile / (1.0 - theta1)

    xi = ((reaction_constants.bg**2) / (4.0 * theta)) ** (1 / 3)

    # Volumetric reaction rate / reactivity 〈σv〉 [m³/s] # noqa: RUF003
    # Original form is in [cm³/s], so multiply by 1.0e-6 to convert to [m³/s]
    sigmav = (
        1.0e-6
        * reaction_constants.cc1
        * theta
        * np.sqrt(xi / (reaction_constants.mrc2 * ion_temperature_profile**3))
        * np.exp(-3.0 * xi)
    )

    # if t = 0, sigmav = 0. Use this mask to set sigmav to zero.
    t_mask = ion_temperature_profile == 0.0  # noqa: RUF069
    sigmav[t_mask] = 0.0

    # Return np.ndarray of sigmav for each point in the ion temperature profile
    return sigmav



