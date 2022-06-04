from abc import ABCMeta
import gym
import gym_cenvs
import numpy as np
from src.simp_mod_library.simp_mod_lib import SimpModLib
from typing import List


class BaseAgent(metaclass=ABCMeta):
    """
    Base class for constructing agents that control the complex object using passed Simple Model Library
    """
    def __init__(self, smodel_list: List[str], device: str = 'cuda:0'):
        # String that is set in derived class
        self.env_name: str = None
        # Ref to step-able mujoco-gym environment
        self.env = None

        # Devices
        self.device = device

        # Dimensionality of an action vector
        self.action_dimension: int = None

        self.model_lib = SimpModLib(smodel_list, device)

        # Keys for the online collected dataset. gt = Ground Truth, ep = episode
        self.data_keys = ["action_history",
                          "gt_state_history"]


        # Container for the episode data collected that is global across agent
        self.episode_data = dict()
        # Initialize all the episode-specific datasets with empty lists
        for data_key in self.data_keys:
            self.episode_data[data_key] = []

    def make_agent_for_task(self):
        """
        Invoked after task specific params have been set in derived class
        :return:
        """
        self.env = gym.make(self.env_name)
        self.env.seed(0)
        self.env.action_space.seed(0)

        # TODO: Infer action dimension from the environment
        #  Check consistency of this dimension with the controls dimension of simple model lib
        self.action_dimension = 1

        return

    @classmethod
    def __new__(cls, *args, **kwargs):
        """
        Make abstract base class non-instaiable
        :param args:
        :param kwargs:
        """
        if cls is BaseAgent:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    def do_episode(self):
        """
        Agent method to online interact with the complex env over an episode
        :return:
        """
        #

        # Reset episode specific parameters
        self.reset_episode()

        done, fail, reward, info = self.step()

    def step(self):
        # Get action from controller
        # Sample states
        # state = self.x_mu.repeat(self.config.controller_N, 1)
        # state = torch.from_numpy(self.true_state_history[-1]).to(device='cuda:0').repeat(self.config.controller_N, 1)
        # state = state.reshape(self.config.controller_N, self.state_dim)
        state = self.x_mu.reshape(1, -1)

        action = np.random.uniform(-1.0, 1.0)

        # print(self.x_mu)

        # print('--')

        self.x_mu, self.x_sigma = self.model_lib['cartpole'].trans_dist.predict(actions[i].view(1, -1), self.x_mu,
                                                                                self.x_sigma)
        # print(self.x_mu)
        # Act in world and get observation
        # TODO for cartpole need to minus action
        observation, reward, done, info = self.env.step(actions[i].detach().cpu().numpy())
        true_state = info['state']
        # print(true_state[:5])
        total_reward += reward
        # Render and update
        z_mu, z_std = self.observation_update(observation)
        # print(z_mu)
        # Log all data from this step
        self.true_state_history.append(true_state)
        self.action_history.append(actions[i].cpu().numpy())
        self.z_mu_history.append(z_mu.cpu().numpy())
        self.z_std_history.append(z_std.cpu().numpy())
        self.img_history.append(observation)

        state_dimension = self.model_lib['cartpole'].cfg.state_dimension

        self.state_cov_history.append(self.x_sigma[0, :state_dimension, :state_dimension].detach().cpu().numpy())
        self.state_mu_history.append(self.x_mu[0, :state_dimension].detach().cpu().numpy())
        self.param_cov_history.append(torch.diag(self.x_sigma[0])[state_dimension:].detach().cpu().numpy())
        self.param_mu_history.append(self.x_mu[0, state_dimension:].detach().cpu().numpy())

        if done:
            return done, False, total_reward, info

        return done, False, total_reward, info

    def reset_episode(self):
        """
        Reset a single episode of interaction with the environment to move on to the next episode
         within the same trial
        :return:
        """
        if self.env is None:
            raise ValueError("Environment has not been made ... cannot reset episode...")

        for data_key in self.data_keys:
            self.episode_data[data_key] = []

        # Frame returned initially from mjco-py environment has a jump from subsequent so ignore it
        _ = self.env.reset()
        obs, _, _, info = self.env.step(np.zeros(self.action_dimension))

        # Reset the episode-specific state of the simple model library
        self.model_lib.reset_episode(obs)

        # Append GT state of complex environment to online collected data
        self.episode_data['gt_state_history'].append(info['state'])

    def reset_trial(self):
        """
        Reset an entire trial for a clean/fresh evaluation of MM-LVSPC
        :return:
        """
        self.model_lib.reset_trial()
