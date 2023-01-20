import math
import random
import numpy as np
import gym
import cv2

from rocket import Rocket
from tvc import TVC
from constants import *


class Curriculum():
    """!
    Used for Curriculum Learning.
    Defines the current settings of the environment.
    """

    def __init__(self):
        """!
        Initializes the curriculum.
        By default:
            a) turning is disabled
            b) rocket starts from a fixed height
            c) rocket starts in an upright position
        """

        self.set_fixed_height()
        self.disable_turn()
        self.disable_random_starting_rotation()
        self.disable_random_height()
        self.disable_x_velocity_reward()
        self.disable_landing_target()

    def set_fixed_height(self):
        """!
        Sets the starting height of the rocket to a fixed number
        """
        self.start_height = STARTING_HEIGHT

    def set_random_height(self, mi, ma):
        """!
        Sets the starting height of the rocket to a fixed number
        """
        self.start_height = STARTING_HEIGHT

        self.min = mi
        self.max = ma

    def disable_random_height(self):
        """!
        Disables rocket's spawn at random height.
        """

        self.fixed_height = True

    def enable_random_height(self):
        """!
        Enables rocket's spawn at random height
        """

        self.fixed_height = False

    def get_height(self):
        """!
        Calculates spawn height of the rocket based on set parameters.

        @return float: rocket's height
        """

        if self.fixed_height:
            return self.start_height
        else:
            return random.uniform(self.min, self.max)

    def disable_x_velocity_reward(self):
        """!
        Disable rewards for velocity in x-axis.
        """

        self.x_velocity_reward = False

    def enable_x_velocity_reward(self):
        """!
        Enable rewards for velocity in x-axis.
        """

        self.x_velocity_reward = True

    def disable_turn(self):
        """!
        Disables rocket's ability to turn the TVC engine
        """
        self.allow_turn = False

    def enable_turn(self):
        """!
        Enables rocket's ability to turn the TVC engine
        """
        self.allow_turn = True

    def enable_random_starting_rotation(self):
        """!
        Enables random starting rotation of a rocket
        """
        self.random_rotation = True

    def disable_random_starting_rotation(self):
        """!
        Disables random starting rotation of a rocket
        """
        self.random_rotation = False

    def enable_landing_target(self):
        """!
        Enable rewards for landing at a target.
        """

        self.land_at_target = True

    def disable_landing_target(self):
        """! 
        Disable rewards for landing at a target.
        """

        self.land_at_target = False


class Environment(gym.Env):
    """!
    Class describing the environment.
    Contains the rocket and the engine mount.
    All the interaction with the environment should happen
    through this module.
    """

    def __init__(self):
        """!
        Constructs the environment.
        """

        super(Environment, self).__init__()

        self.canvas_shape = (1500, 1200, 3)
        self.canvas = np.ones(shape=self.canvas_shape) * 1

        self.curriculum = Curriculum()
        self.reset()

    def reset(self):
        """!
        Resets the environment to conditions defined
        by curriculum and predefined constants

        @return list: current state of the environment
        """

        start_dx = 0
        start_dy = 1
        if self.curriculum.random_rotation:
            start_dx = random.uniform(-0.5, 0.5)
            start_dy = random.uniform(0.5, 1)

        start_position = 0
        if self.curriculum.land_at_target:
            start_position = random.uniform(-3, 3)

        self.rocket = Rocket(start_position, self.curriculum.get_height(), WEIGHT,
                             MOMENT_OF_INERTIA, CENTER_OF_MASS, dir_x=start_dx, dir_y=start_dy)
        self.tvc = TVC(MAX_THRUST, THRUST_CHANGE_PER_SECOND,
                       ROTATION_SPEED_PER_SECOND, dir_x=start_dx, dir_y=start_dy)

        self.timestep = 0

        self.close()

        return self.__get_state()

    def step(self, action, it):
        """!
        Updates the environment for one timestep.

        @param action (Action): _description_

        @return list: newly observed state of the environment
        @return float: sampled reward
        @return boolean: whether or not the simulation is finished
        """

        if action == Action.LEFT:
            self.tvc.set_rotation_left()
            self.tvc.current_thrust = MAX_THRUST
        elif action == Action.MIDDLE:
            self.tvc.set_rotation_middle()
            self.tvc.current_thrust = MAX_THRUST
        elif action == Action.RIGHT:
            self.tvc.set_rotation_right()
            self.tvc.current_thrust = MAX_THRUST
        else:
            self.tvc.current_thrust = 0

        self.rocket.update_position(self.tvc)
        self.rocket.log(self.tvc, self.timestep)

        reward = 0
        reward -= 0.0001

        if self.rocket.position_y <= 0:
            reward = 6 + self.rocket.velocity_y - \
                self.rocket.get_unsigned_angle_with_y_axis() - \
                0.2*abs(self.rocket.angular_velocity)

            if self.curriculum.x_velocity_reward:
                reward -= 0.5 * abs(self.rocket.velocity_x)

            if self.curriculum.land_at_target:
                reward -= 0.05 * abs(self.rocket.position_x)

        self.timestep += TIMESTEP

        return self.__get_state(), reward, self.rocket.position_y <= 0 or abs(self.rocket.position_x) > 10 or self.rocket.y < 0

    def render(self, mode="human"):
        """!
        Renders the current state to a human-readable image.

        @param mode (string): "human" to display, "rgb-array" to get a 2D array

        @return: 2D array with image if rgb-array mode is selected.
        """

        self.__draw_on_canvas()

        assert mode in ["human", "rgb_array"]

        if mode == "human":
            cv2.imshow("Rocket landing", self.canvas)
            cv2.waitKey(int(1000*TIMESTEP))

        elif mode == "rgb_array":
            return self.canvas

    def close(self):
        """!
        Destroys all windows.
        """

        cv2.destroyAllWindows()
        cv2.waitKey(1)

    def __draw_on_canvas(self):
        """!
        Draws all objects on canvas to render
        """

        GROUND_HEIGHT = 60

        screen_rocket_pos_y = int(
            self.canvas_shape[0] - (self.rocket.position_y * 55)) - self.rocket.icon_idle.shape[0]
        screen_rocket_pos_x = int(
            (self.rocket.position_x + 11) * 55) - self.rocket.icon_idle.shape[1]//2

        if screen_rocket_pos_x < 0:
            return
        if screen_rocket_pos_y < 0:
            return

        if screen_rocket_pos_x + self.rocket.icon_idle.shape[1] >= self.canvas_shape[1]:
            return
        if screen_rocket_pos_y + self.rocket.icon_idle.shape[0] >= self.canvas_shape[0]:
            return

        self.canvas = np.ones(shape=self.canvas_shape)

        rot_mat = cv2.getRotationMatrix2D(
            (self.rocket.icon_idle.shape[1]//2, self.rocket.icon_idle.shape[0]//2), math.degrees(-self.rocket.get_signed_angle_with_y_axis()), 1.0)

        if self.tvc.current_thrust == 0:
            rocket_icon = cv2.warpAffine(
                self.rocket.icon_idle, rot_mat, self.rocket.icon_idle.shape[1::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        elif abs(self.tvc.level) < 0.01:
            rocket_icon = cv2.warpAffine(
                self.rocket.icon_mid, rot_mat, self.rocket.icon_idle.shape[1::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        elif self.tvc.level < 0:
            rocket_icon = cv2.warpAffine(
                self.rocket.icon_left, rot_mat, self.rocket.icon_idle.shape[1::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        elif self.tvc.level > 0:
            rocket_icon = cv2.warpAffine(
                self.rocket.icon_right, rot_mat, self.rocket.icon_idle.shape[1::-1], flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

        self.canvas[screen_rocket_pos_y: screen_rocket_pos_y + self.rocket.icon_idle.shape[0],
                    screen_rocket_pos_x: screen_rocket_pos_x + self.rocket.icon_idle.shape[1]] = rocket_icon / 255

        self.canvas[self.canvas.shape[0] -
                    GROUND_HEIGHT:self.canvas.shape[0], 0:self.canvas.shape[1]] = 0

        self.canvas[self.canvas.shape[0] -
                    GROUND_HEIGHT:self.canvas.shape[0] -
                    GROUND_HEIGHT+10, self.canvas.shape[1]//2-20:self.canvas.shape[1]//2+20, 2] = 255

    def __get_state(self):
        """!
        Generates a vector describing the environment

        @return list: description of the environment
        """

        state = []
        state.append(STARTING_HEIGHT - self.rocket.position_y)
        state.append(self.rocket.velocity_y)
        state.append(self.rocket.velocity_x)
        state.append(self.rocket.position_x)
        state.append(self.rocket.angular_velocity)
        state.append(self.rocket.get_signed_angle_with_y_axis())

        return state

    def __str__(self):
        along, side = self.rocket.get_rotated_vectors()
        return f"Environment:\n\tRocket: {self.rocket}\n\tTVC: {self.tvc}\n\tImpact on rocket: \n\t\tPush: {self.tvc.current_thrust * self.tvc.get_component_along_vector(along):.2f} N\n\t\tRotate: {self.tvc.current_thrust * self.tvc.get_component_along_vector(side):.2f} N"
