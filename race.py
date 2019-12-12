import argparse
import numpy as np
import time
from PIL import Image
from collections import deque
from pathlib import Path

import Adafruit_PCA9685
# noinspection PyUnresolvedReferences
from keras.models import load_model

from utils.pivideostream import PiVideoStream
from utils.const import SPEED_NORMAL, SPEED_FAST, HEAD_UP, HEAD_DOWN, \
    DIRECTION_R, DIRECTION_L, DIRECTION_C, DIRECTION_L_M, DIRECTION_R_M


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=str,
                        help="Provide the model path.\n")
    parser.add_argument("-t", "--trial", action="store_true",
                        help="Run in trail mode: record las 'buff_size' picture and measure pred rate.\n")
    return parser.parse_args()


class RaceOn:
    def __init__(self, model_path):
        # Racing_status
        self.racing = False

        # Load model
        self.model = load_model(model_path)

        # Init engines
        # TODO (pclement): A quoi sert direction speed? ajouterhead pour initialiser
        self.speed = SPEED_FAST
        self.direction = DIRECTION_C
        self.head = HEAD_DOWN
        self.pwm = Adafruit_PCA9685.PCA9685()
        self.pwm.set_pwm_freq(50)

        # Create a *threaded *video stream, allow the camera sensor to warm_up
        self.video_stream = PiVideoStream().start()
        time.sleep(2)
        self.video_stream.test()
        self.frame = self.video_stream.read()
        self.buffer = None
        self.nb_pred = 0
        self.start_time = 0
        print("RaceOn initialized")

    @staticmethod
    def choose_direction(predictions):
        # TODO (pclement): Make it more modular so it can handle 3 or 5 direction--> dictionnary or list in utils.const?
        if predictions[1] == 0:
            return DIRECTION_L_M
        elif predictions[1] == 1:
            return DIRECTION_L
        elif predictions[1] == 2:
            return DIRECTION_C
        elif predictions[1] == 3:
            return DIRECTION_R
        elif predictions[1] == 4:
            return DIRECTION_R_M

    @staticmethod
    def choose_speed(predictions):
        if predictions[1] == 1 and predictions[0] == 1:
            return SPEED_FAST
        return SPEED_NORMAL

    @staticmethod
    def choose_head(predictions, speed):
        if speed == SPEED_FAST and predictions[1] == 1 and predictions[0] == 1:
            return HEAD_UP
        return HEAD_DOWN

    def race_trial(self, buff_size=100):
        self.buffer = deque(maxlen=buff_size)
        self.start_time = time.time()
        while True:
            # Grab the self.frame from the threaded video stream
            self.frame = self.video_stream.read()
            sample = {"array": self.frame}
            image = np.array([self.frame]) / 255.0  # [jj] Do we need to create a new array ? img = self.frame / 255. ?

            # Get model prediction
            predictions_raw = self.model.predict(image)
            predictions = [np.argmax(pred, axis=1) for pred in predictions_raw]  # Why ?

            # Decide action
            direction = self.choose_direction(predictions)
            speed = self.choose_speed(predictions)
            head = self.choose_head(predictions, speed)
            sample["direction"] = predictions[1]
            sample["speed"] = 1 if speed == SPEED_FAST else 0
            self.buffer.append(sample)

            # Apply values to engines
            self.pwm.set_pwm(0, 0, direction)
            self.pwm.set_pwm(1, 0, speed)
            self.nb_pred += 1

    def race(self, show_pred=False):
        speed = SPEED_NORMAL
        self.racing = True
        while self.racing:
        # Grab the self.frame from the threaded video stream
            self.frame = self.video_stream.read()
            image = np.array([self.frame]) / 255.0  # [jj] Do we need to create a new array ? img = self.frame / 255. ?

            # Get model prediction
            predictions_raw = self.model.predict(image)
            predictions = [np.argmax(pred, axis=1) for pred in predictions_raw]  # Why ?

            # Decide action
            direction = self.choose_direction(predictions)
            head = self.choose_head(predictions, speed)
            speed = self.choose_speed(predictions)

            if show_pred:
                print("""Predictions = {}
                Direction = {}, Head = {}, Speed = {}""".format(predictions, direction, head, speed))

            # Apply values to engines
            self.pwm.set_pwm(0, 0, direction)
            self.pwm.set_pwm(1, 0, speed)
            self.pwm.set_pwm(2, 0, head)
            self.nb_pred += 1

    # TODO (pclement) reinitialize to init values
    def stop(self):
        self.racing = False
        self.pwm.set_pwm(0, 0, 0)
        self.pwm.set_pwm(1, 0, 0)
        self.pwm.set_pwm(2, 0, 0)
        self.video_stream.stop()

        # Performance status
        elapse_time = time.time() - self.start_time
        pred_rate = self.nb_pred / float(elapse_time)
        print('{} prediction in {}s -> {} pred/s'.format(self.nb_pred, elapse_time, pred_rate))

        # Write buffer
        if self.buffer is not None and len(self.buffer) > 0:
            output_folder = Path("output")
            print('Saving buffer pictures to : "{}"'.format(output_folder))
            for i, img in enumerate(self.buffer):
                pic_file = Path('{}_{}_image{}.jpg'.format(img["speed"], img["direction"], i))
                pic = Image.fromarray(img["array"], 'RGB')
                pic.save(output_folder / pic_file)
            print('{} pictures saved.'.format(i + 1))
        print("Stop")


if __name__ == '__main__':
    options = get_args()
    race_on = None
    try:
        race_on = RaceOn(options.model_path)
        print("Are you ready ?")

        # TODO (pclement): other inputs to stop the motor & direct the wheels without having to reload the full model.

        starting_prompt = """Press 'go' + enter to start.
        Press 'show' + enter to start with the printing mode.
        Press 'q' + enter to totally stop the race.
        """
        racing_prompt = """Press 'q' + enter to totally stop the race\n"""
        keep_going = True
        started = False
        while keep_going:
            try:  # This is for python2
                # noinspection PyUnresolvedReferences
                user_input = raw_input(racing_prompt) if started else raw_input(starting_prompt)
            except NameError:
                user_input = input(racing_prompt) if started else input(starting_prompt)
            if user_input == "go" and not started:
                print("Race is on.")
                race_on.race(show_pred=False)
                started = True
            elif user_input == "show" and not started:
                print("Race is on. test mode")
                race_on.race_trial()
                # race_on.race(show_pred=True)
                started = True
            elif user_input == "q":
                keep_going = False
    except KeyboardInterrupt:
        pass
    finally:
        if race_on:
            race_on.stop()
        print("Race is over.")
