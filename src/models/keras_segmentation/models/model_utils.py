from types import MethodType

import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.layers import Activation, Permute, Reshape
from tensorflow.keras.models import Model
from tqdm import tqdm

from ..predict import evaluate, predict, predict_multiple
from ..train import train
from .config import IMAGE_ORDERING


# source m1 , dest m2
def transfer_weights(m1, m2, verbose=True):

    assert len(m1.layers) == len(
        m2.layers
    ), "Both models should have same number of layers"

    nSet = 0
    nNotSet = 0

    if verbose:
        print("Copying weights ")
        bar = tqdm(zip(m1.layers, m2.layers))
    else:
        bar = zip(m1.layers, m2.layers)

    for layer_1, layer_2 in bar:

        if not any(
            [
                w.shape != ww.shape
                for w, ww in zip(list(layer_1.weights), list(layer_2.weights))
            ]
        ):
            if len(list(layer_1.weights)) > 0:
                layer_2.set_weights(layer_1.get_weights())
                nSet += 1
        else:
            nNotSet += 1

    if verbose:
        print(
            "Copied weights of %d layers and skipped %d layers"
            % (nSet, nNotSet)
        )


def resize_image(inp, s, data_format):
    return (
        lambda x: K.resize_images(
            x,
            height_factor=s[0],
            width_factor=s[1],
            data_format=data_format,
            interpolation="bilinear",
        )
    )(inp)


def get_segmentation_model(input, output):
    img_input = input
    o = output

    # VVV  Add this VVV
    size_before3 = tf.keras.backend.int_shape(img_input)
    o = tf.keras.layers.experimental.preprocessing.Resizing(
        *size_before3[1:3], interpolation="bilinear"
    )(o)
    # ^^^  Add this ^^^

    o_shape = Model(img_input, o).output_shape
    i_shape = Model(img_input, o).input_shape

    if IMAGE_ORDERING == "channels_first":
        output_height = o_shape[2]
        output_width = o_shape[3]
        input_height = i_shape[2]
        input_width = i_shape[3]
        n_classes = o_shape[1]
        o = (Reshape((output_height, output_width, n_classes)))(o)
        o = (Permute((2, 1)))(o)
    elif IMAGE_ORDERING == "channels_last":
        output_height = o_shape[1]
        output_width = o_shape[2]
        input_height = i_shape[1]
        input_width = i_shape[2]
        n_classes = o_shape[3]
        o = (Reshape((output_height, output_width, n_classes)))(o)

    o = (Activation("softmax", dtype="float32"))(o)
    model = Model(img_input, o)
    model.output_width = output_width
    model.output_height = output_height
    model.n_classes = n_classes
    model.input_height = input_height
    model.input_width = input_width
    model.model_name = ""

    model.train = MethodType(train, model)
    model.predict_segmentation = MethodType(predict, model)
    model.predict_multiple = MethodType(predict_multiple, model)
    model.evaluate_segmentation = MethodType(evaluate, model)

    return model
