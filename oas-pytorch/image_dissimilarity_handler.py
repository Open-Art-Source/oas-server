from abc import ABC
import io
import base64
import torch
from PIL import Image
from captum.attr import IntegratedGradients
from ts.torch_handler.base_handler import BaseHandler
from torchvision import transforms
import torch.nn.functional as F


class ImageDissimilarityHandler(BaseHandler, ABC):

    # resize to 256 x 256
    image_processing = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(256),
        transforms.ToTensor()
    ])


    """
    Base class for all vision handlers
    """
    def initialize(self, context):
        super().initialize(context)
        self.ig = IntegratedGradients(self.model)
        self.initialized = True


    def preprocess(self, data):
        """The preprocess function of MNIST program converts the input data to a float tensor
        Args:
            data : Input data from the request
                    List of {'image-0': ByteArray, 'image-1': ByteArray}
        Returns:
            tuple of two stacked tensors, one for all the images0s and the other for all image1s
        """
        image0s = []
        image1s = []

        for row in data:
            # Compat layer: normally the envelope should just return the data
            # directly, but older versions of Torchserve didn't have envelope.

            image0 = row.get('image-0')
            image1 = row.get('image-1')

            if isinstance(image0, str):
                # if the image is a string of bytesarray.
                image0 = base64.b64decode(image0)
                image1 = base64.b64decode(image1)
                print('XXXXXXXXXXXXXXXXXX the image is a string of bytesarray.')

            # If the image is sent as bytesarray
            if isinstance(image0, (bytearray, bytes)):
                image0 = Image.open(io.BytesIO(image0))
                image0 = self.image_processing(image0)
                image1 = Image.open(io.BytesIO(image1))
                image1 = self.image_processing(image1)
                print('XXXXXXXXXXXXXXXXXX the image is sent as bytesarray')
            else:
                # if the image is a list
                image0 = torch.FloatTensor(image0)
                image1 = torch.FloatTensor(image1)
                print('XXXXXXXXXXXXXXXXXX the image is a list')

            image0s.append(image0)
            image1s.append(image1)

        return torch.stack(image0s), torch.stack(image1s)


    def inference(self, data, *args, **kwargs):
        """
        The Inference Function is used to make a prediction call on the given input request.
        The user needs to override the inference function to customize it.

        Args:
            data (Torch Tensor): A Torch Tensor is passed to make the Inference Request.
            The shape should match the model input shape.

        Returns:
            Torch Tensor : The Predicted Torch Tensor is returned in this function.
        """

        image0s, image1s = data

        with torch.no_grad():
            image0s = image0s.to(self.device, dtype=torch.float32)
            image1s = image1s.to(self.device, dtype=torch.float32)
            output0 = self.model(image0s, *args, **kwargs)
            output1 = self.model(image1s, *args, **kwargs)
            #compute the euclidean distance to see the dissimilarity between the two output images
            eucledian_distances = F.pairwise_distance(output0, output1)

        return eucledian_distances

    def get_insights(self, tensor_data, _, target=0):
        print("input shape", tensor_data.shape)
        return self.ig.attribute(tensor_data, target=target, n_steps=15).tolist()