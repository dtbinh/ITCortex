# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt

def get_poisson_spikes(dt, rates):
    """
    Poisson approximation via Bernoulli process.

    :param dt: Size of time step (s; should be ~1ms)
    :param rates: List of neuron spike rates (spikes / s)
    :return: List of random spike events (0 = no spike; 1 = spike)
    """
    assert len(rates.shape) == 1
    # noinspection PyArgumentList
    return np.random.rand(len(rates)) < (dt * rates)


def integrate(dt, a, b, c, x, u):
    """
    Euler integration of state-space equations.

    :param dt: Time step (s; should be ~5ms)
    :param a: The standard feedback matrix from linear-systems theory
    :param b: Input matrix
    :param c: Output matrix
    :param x: State vector
    :param u: Input vector
    :return: (x, y), i.e. the state and the output
    """

    dxdt = np.dot(a,x) + np.dot(b,u)
    x = x + dxdt*dt
    y = np.dot(c,x)
    return x, y

# noinspection PyArgumentList
class TamuraDynamics :
    """
    Simple model of IT spike-rate tamura_dynamic_profile.py based on:

    Tamura, H., & Tanaka, K. (2001). Visual response properties of cells in the ventral
        and dorsal parts of the macaque inferotemporal cortex. Cerebral Cortex, 11(5), 384–399.

    Some key points from this paper are:
      1) There are usually two response phases, early (transient) and late (sustained)
      2) Selectivity is higher in late phase than early phase
      3) There is heterogeneity in the ratio of early to late magnitude, but peak
        early responses are typically higher (note: this probably arises at least
        in part from selectivity)
      4) Response latency is negatively correlated with peak response magnitude

    There are many other interesting dynamic phenomena that we don't model here, including from:

    Brincat, S. L., & Connor, C. E. (2006). Dynamic shape synthesis in posterior inferotemporal
        cortex. Neuron, 49(1), 17–24.
    Kiani, R., Esteky, H., & Tanaka, K. (2005). Differences in onset latency of macaque
        inferotemporal neural responses to primate and non-primate faces. Journal of
        Neurophysiology, 94(2), 1587–1596.
    Matsumoto, N., Okada, M., Sugase-Miyamoto, Y., Yamane, S., & Kawano, K. (2005). Population
        dynamics of face-responsive neurons in the inferior temporal cortex. Cerebral Cortex,
        15(8), 1103–1112.
    Ringo, J. L. (1996). Stimulus specific adaptation in inferior temporal and medial temporal
        cortex of the monkey, 76, 191–197.
    """
    def __init__(self, dt, obj_dict, max_latency=0.25):
        """
        :param dt           : Simulation time step in seconds.
        :param obj_dict     : Dictionary of {object: selectivity} for the neuron.
                              Selectivity ranges between (0, 1) and is the normalized firing rate
                              of the neuron to the specified object.
        :param max_latency  : maximum response latency of the neuron. Default = 0.25s
        """
        self.dt = dt

        self.type = 'Tamura_dynamic_profile'

        self.early_obj_pref = self.get_early_object_selectivities(obj_dict)

        # parameters of exponential functions to map static rate to latency for each neuron
        self.min_latencies = .09 + .01*np.random.rand(1)
        self.max_latencies = np.minimum(max_latency,
                                        self.min_latencies + np.random.gamma(5, .02, 1))

        self.tau_latencies = np.random.gamma(2, 20, 1)

        # matrices for storing recent input history, to allow variable-latency responses
        self.late_additional_latency = 10
        latency_steps = max_latency/dt + 1 + self.late_additional_latency
        self.early_memory = np.zeros((1, latency_steps))
        self.late_memory = np.zeros((1, latency_steps))
        self.memory_index = 0

        # state-space LTI dynamics (early response is band-pass and late response is low-pass)
        self.early_tau = np.maximum(.005, .017 + .005*np.random.randn(1))
        self.late_tau = .05 + .01*np.random.randn(1)
        early_gain = 1.5/0.39
        late_gain = 1

        # these are templates that must be multiplied by 1/tau for each neuron ...
        self.early_A = np.array([[-1, 0], [1, -1]])
        self.early_B = np.array([1, 0])
        self.late_A = -1
        self.late_B = 1

        self.early_C = np.array([early_gain, -early_gain])
        self.late_C = late_gain

        # state of LTI (linear time-invariant) dynamical systems
        self.early_x = np.zeros((2, 1))
        self.late_x = np.zeros(1)

    @staticmethod
    def get_early_object_selectivities(late_obj_dict):
        """
        Given a dictionary of {object: default (late) latency} create a similar dictionary for
        early response latencies that shows the observed lower selectivities in initial responses.

        The selectivity for each object is doubled and constrained to lie within (0, 1).

        :param late_obj_dict: Dictionary of {object: selectivity} for the neuron. Selectivity
            ranges between (0, 1) and is the normalized firing rate of the neuron to the
            specified object.
        """
        return { key: np.minimum(value*2, 1) for key, value in late_obj_dict.items()}


    def get_dynamic_rates(self, early_rates, late_rates):
        """
        :param early_rates: Static rates for versions of the neurons with early selectivity
        :param late_rates: Static rates for versions of the neurons with late selectivity
        :return: Spike rates with latency and early and late dynamics
        """

        self.early_memory[:, self.memory_index] = early_rates
        self.late_memory[:, self.memory_index] = late_rates

        latencies = self._get_latencies(early_rates)

        early_u, late_u = self._get_lagged_rates(latencies)

        self.memory_index += 1
        if self.memory_index == self.early_memory.shape[1]:
            self.memory_index = 0

        return self._step_dynamics(early_u, late_u)

    def _get_lagged_rates(self, latencies):
        # get appropriately lagged rates for input to LTI dynamics
        latency_steps = np.rint(latencies / self.dt).astype('int')

        early_indices = self._get_index(latency_steps)
        late_indices = self._get_index(latency_steps + self.late_additional_latency)

        # early_u = self.early_memory[range(1), early_indices][0]
        # late_u = self.late_memory[range(1), late_indices][0]
        early_u = self.early_memory[range(1), early_indices]
        late_u = self.late_memory[range(1), late_indices]

        return early_u, late_u

    def _step_dynamics(self, early_u, late_u):
        # run a single step of the LTI dynamics for each neuron
        y = np.zeros(1)

        for ii in range(1):
            early_a = 1/self.early_tau[ii] * self.early_A
            early_b = 1/self.early_tau[ii] * self.early_B
            self.early_x[:, ii], early_y = integrate(
                self.dt,
                early_a,
                early_b,
                self.early_C,
                self.early_x[:, ii],
                early_u[ii])

            late_a = 1/self.late_tau[ii] * self.late_A
            late_b = 1/self.late_tau[ii] * self.late_B

            self.late_x[ii], late_y = integrate(
                self.dt,
                late_a,
                late_b,
                self.late_C,
                self.late_x[ii],
                late_u[ii])

            y[ii] = np.maximum(0, early_y) + late_y

        return y

    def _get_index(self, latency_steps):
        index = self.memory_index - np.minimum(latency_steps, self.early_memory.shape[1])
        index[index < 0] = index[index < 0] + self.early_memory.shape[1]
        return index

    def _get_latencies(self, static_rates):
        # latency varies with response strength
        return self.min_latencies + \
               (self.max_latencies - self.min_latencies)*np.exp(-static_rates/self.tau_latencies)

    def plot_latencies_verses_rate_profile(self,  axis=None):
        """
        Plot fire latency as a function of static fire rate.

        :param axis: Python axis object for where to plot. Useful for adding contour plot
                     as a subplot in an image. Default = None.
        """
        if axis is None:
            fig, axis = plt.subplots()

        rate = np.arange(0, 200, 10)
        fire_start_latencies = np.zeros((len(rate)))

        for ii in range(len(rate)):
            fire_start_latencies[ii] = self._get_latencies(rate[ii])

        axis.set_title("Spike rates vs start_latencies")
        axis.plot(rate, fire_start_latencies)
        axis.set_xlabel('Early Response Rate (spikes / s)')
        axis.set_ylabel('Response Latency (s)')

    def get_ranked_object_list(self):
        """ Return neurons rank list of objects and rate modification factors """
        return sorted(self.early_obj_pref.items(), key=lambda item: item[1], reverse=True)

    def print_parameters(self):
        """ Print parameters of the profile """
        print("Profile                                   = %s" % self.type)
        print("minimum latency                           = %0.4f" % np.float(self.min_latencies))
        print("maximum latency                           = %0.4f" % self.max_latencies)
        print("tau latency                               = %0.4f" % self.tau_latencies)

        print("Early tau                                 = %0.4f" % self.early_tau)
        print("Late tau                                  = %0.4f" % self.late_tau)
        print("Memory size                               = %d" % self.early_memory.shape[1])

        # TODO: Add these metrics for the early response
        # print("Sparseness(absolute activity fraction)  = %0.4f"
        #       % self.activity_fraction_absolute)
        # print("Sparseness(measured activity fraction)  = %0.4f"
        #       % self.activity_fraction_measured)
        # print("Sparseness (kurtosis)                   = %0.4f" % self.kurtosis)

        print("Early Object Preferences                  = ")

        max_name_length = np.max([len(name) for name in self.early_obj_pref.keys()])

        lst = self.get_ranked_object_list()
        for obj, rate in lst:
            print ("\t%s : %0.4f" % (obj.ljust(max_name_length), rate))


if __name__ == '__main__':
    plt.ion()

    time_step = .005

    default_obj_pref = {'Truck'          : 0.0902061634469222,
                        'bus'            : 0.60042052408207613,
                        'car'            : 0.41523454488601136,
                        'cyclist'        : 0.36497039000201714,
                        'pedestrian'     : 0.18954386060352452,
                        'person sitting' : 0.18705214386720551,
                        'tram'           : 0.24122725774540257,
                        'van'            : 0.42843038621161039}

    d = TamuraDynamics(time_step, default_obj_pref)

    d.print_parameters()

    # plot latency vs. static rate for each neuron ...
    d.plot_latencies_verses_rate_profile()

    # run some neurons with square-pulse input ...
    steps = 200
    early_fire_rates = np.zeros((1, steps))
    early_fire_rates[:,20:100] = 50
    late_fire_rates = early_fire_rates / 2
    early_fire_rates = early_fire_rates * np.random.rand(1, 1)
    late_fire_rates = late_fire_rates * np.random.rand(1, 1)

    time = time_step * np.array(range(steps))
    dynamic_rates = np.zeros_like(early_fire_rates)
    for i in range(steps):
        dynamic_rates[:, i] = d.get_dynamic_rates(early_fire_rates[:, i], late_fire_rates[:, i])

    plt.figure("Dynamic fire rates")
    plt.plot(time, dynamic_rates.T)
    plt.xlabel('Time (s)')
    plt.ylabel('Spike Rate (spikes / s)')

    plt.plot(time, early_fire_rates.T, label = 'Early fire rate')
    plt.plot(time, late_fire_rates.T, label = 'Late fire rate')
    plt.legend()
