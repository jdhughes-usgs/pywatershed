import pathlib as pl
import shutil
from typing import Union, Literal


from . import _is_pws, parameterized, test_data_dir

if _is_pws:
    import pywatershed as pws
else:
    import pynhm as pws


domains = ["hru_1", "drb_2yr", "ucb_2yr"]
outputs = [None, "separate", "together"]
n_time_steps = 183

model_tests = {
    "solar": (pws.PRMSSolarGeometry,),
    "atm": (pws.PRMSAtmosphere,),
    "canopy": (pws.PRMSCanopy,),
    "snow": (pws.PRMSSnow,),
    "runoff": (pws.PRMSRunoff,),
    "soil": (pws.PRMSSoilzone,),
    "gw": (pws.PRMSGroundwater,),
    "channel": (pws.PRMSChannel,),
    "nhm": (
        pws.PRMSSolarGeometry,
        pws.PRMSAtmosphere,
        pws.PRMSCanopy,
        pws.PRMSSnow,
        pws.PRMSRunoff,
        pws.PRMSSoilzone,
        pws.PRMSGroundwater,
        pws.PRMSChannel,
    ),
}
model_tests_inv = {v: k for k, v in model_tests.items()}


class PRMSBasics:
    """Benchmark simple components object of PRMS models"""

    @parameterized(
        ["domain"],
        (domains),
    )
    def time_prms_parameter_read(self, domain):
        parameter_file = test_data_dir / f"{domain}/myparam.param"
        if _is_pws:
            _ = pws.parameters.PrmsParameters.load(parameter_file)
        else:
            _ = pws.PrmsParameters.load(parameter_file)
        return

    @parameterized(
        ["domain"],
        (domains),
    )
    def time_prms_control_read(self, domain):
        control_file = test_data_dir / f"{domain}/control.test"
        _ = pws.Control.load(control_file)
        return


class PRMSModels:
    """Benchmark simple components object of PRMS models"""

    def setup(self, *args):
        self.domain = args[0]
        self.processes = args[1]
        self.tag = model_tests_inv[self.processes]

        self.control_file = test_data_dir / f"{self.domain}/control.test"
        self.parameter_file = test_data_dir / f"{self.domain}/myparam.param"
        print(f"model_setup_run tag: {self.tag}")
        if _is_pws:
            params = pws.parameters.PrmsParameters.load(self.parameter_file)
        else:
            params = pws.PrmsParameters.load(self.parameter_file)

        self.control = pws.Control.load(self.control_file, params=params)
        self.control.edit_n_time_steps(n_time_steps)

        # setup input_dir with symlinked prms inputs and outputs
        self.domain_dir = pl.Path(f"PRMSModels_{self.domain}")
        self.domain_dir.mkdir(exist_ok=True)
        self.tag_dir = self.domain_dir / self.tag
        self.tag_input_dir = self.tag_dir / "input"
        self.tag_input_dir.mkdir(parents=True)
        for ff in (test_data_dir / self.domain).glob("*.nc"):
            shutil.copy(ff, self.tag_input_dir / ff.name)
            for ff in (test_data_dir / f"{self.domain}/output").glob("*.nc"):
                shutil.copy(ff, self.tag_input_dir / ff.name)

    def teardown(self, *args):
        shutil.rmtree(self.domain_dir)
        pass

    # Helper function
    def model_setup_run(
        self,
        domain: str = None,
        processes: tuple = None,
        write_output: Union[bool, Literal["separate", "together"]] = None,
    ):
        model = pws.Model(
            *self.processes,
            control=self.control,
            input_dir=self.tag_input_dir,
            budget_type="warn",
            calc_method="numba",
        )
        if write_output is not None:
            model.initialize_netcdf(
                self.tag_dir, separate_files=(write_output == "separate")
            )
        model.run(finalize=True)

    @parameterized(
        ["domain", "processes", "output"],
        (
            domains,
            list(model_tests.values()),
            outputs,
        ),
    )
    def time_prms_run(
        self,
        domain: str,
        processes: tuple,
        output: Union[None, Literal["separate", "together"]],
    ):
        _ = self.model_setup_run(
            domain=domain, processes=processes, write_output=output
        )