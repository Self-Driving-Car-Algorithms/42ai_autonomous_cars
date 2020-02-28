#  Patate/Data_processing/Training/3_directions_models_Opti_speed.ipynb

# noinspection PyPep8Naming
import tensorflow.keras.backend as K
from tensorflow.keras.layers import Convolution2D, BatchNormalization, Activation, Dropout, Flatten, Input, Dense


def get_model_params():
    # TODO (pclement): play with models this is Model from PatateV2

    K.clear_session()
    img_in = Input(shape=(96, 160, 3), name='img_in')
    x = img_in

    x = Convolution2D(2, (5, 5), strides=(2, 2), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = Convolution2D(4, (5, 5), strides=(2, 2), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = Dropout(.4)(x)
    x = Convolution2D(8, (5, 5), strides=(2, 2), use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = Dropout(.5)(x)

    x = Flatten(name='flattened')(x)

    x = Dense(100, use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = Dropout(.4)(x)
    x = Dense(50, use_bias=False)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = Dropout(.3)(x)

    out_dir = Dense(3, activation='softmax')(x)
    out_speed = Dense(2, activation='softmax')(x)

    model_parameters = {
        'model_name': "model_race_speed.h5",
        'model_inputs': [img_in],
        'model_outputs': [out_speed, out_dir],
    }
    return model_parameters


if __name__ == '__main__':
    model_params = get_model_params()
    print(model_params)