import pathlib as pl

import numpy as np
import pytest

from pywatershed.base.adapter import adapter_factory
from pywatershed.base.control import Control
from pywatershed.hydrology.prms_runoff import PRMSRunoff
from pywatershed.parameters import Parameters, PrmsParameters

calc_methods = ("numpy", "numba")
params = ("params_sep", "params_one")


@pytest.fixture(scope="function")
def control(domain):
    return Control.load(domain["control_file"])


@pytest.fixture(scope="function")
def discretization(domain):
    dis_hru_file = domain["dir"] / "parameters_dis_hru.nc"
    return Parameters.from_netcdf(dis_hru_file, encoding=False)


@pytest.fixture(scope="function", params=params)
def parameters(domain, request):
    if request.param == "params_one":
        params = PrmsParameters.load(domain["param_file"])
    else:
        param_file = domain["dir"] / "parameters_PRMSRunoff.nc"
        params = PrmsParameters.from_netcdf(param_file)

    return params


@pytest.mark.parametrize("calc_method", calc_methods)
def test_compare_prms(
    domain, control, discretization, parameters, tmp_path, calc_method
):
    tmp_path = pl.Path(tmp_path)

    # get the answer data

    comparison_var_names = [
        "infil",
        "infil_hru",
        "dprst_stor_hru",
        "dprst_seep_hru",
        "hru_impervstor",
        "sroff",
        "dprst_evap_hru",
        "hru_impervevap",
    ]
    output_dir = domain["prms_output_dir"]

    # Read PRMS output into ans for comparison with pywatershed results
    ans = {}
    for key in comparison_var_names:
        nc_pth = output_dir / f"{key}.nc"
        ans[key] = adapter_factory(nc_pth, variable_name=key, control=control)

    # instantiate runoff
    input_variables = {}
    for key in PRMSRunoff.get_inputs():
        nc_pth = output_dir / f"{key}.nc"
        input_variables[key] = nc_pth

    runoff = PRMSRunoff(
        control=control,
        discretization=discretization,
        parameters=parameters,
        calc_method=calc_method,
        **input_variables,
        budget_type="warn",  # intermittent errors currently
    )

    all_success = True
    for istep in range(control.n_times):
        control.advance()
        runoff.advance()
        runoff.calculate(1.0)

        # advance the answer, which is being read from a netcdf file
        for key, val in ans.items():
            val.advance()

        # make a comparison check with answer
        check = True
        failfast = True
        detailed = True
        if check:
            atol = 1.0e-5
            success = check_timestep_results(
                runoff, istep, ans, atol, detailed
            )
            if not success:
                all_success = False
                if failfast:
                    assert success, "stopping..."

    runoff.finalize()

    # check at the end and error if one or more steps didn't pass
    if not all_success:
        raise Exception("pywatershed results do not match prms results")

    return


def check_timestep_results(storageunit, istep, ans, atol, detailed=False):
    all_success = True
    for key in ans.keys():
        a1 = ans[key].current
        a2 = storageunit[key]
        success = np.isclose(a1, a2, atol=atol).all()
        if not success:
            all_success = False
            diff = a1 - a2
            diffmin = diff.min()
            diffmax = diff.max()
            if True:
                print(f"time step {istep}")
                print(f"output variable {key}")
                print(f"prms   {a1.min()}    {a1.max()}")
                print(f"pywatershed  {a2.min()}    {a2.max()}")
                print(f"diff   {diffmin}  {diffmax}")
                if detailed:
                    idx = np.where(np.abs(diff) > atol)[0]
                    for i in idx:
                        print(
                            f"hru {i} prms {a1[i]} pywatershed {a2[i]} diff {diff[i]}"
                        )
            asdf
    return all_success