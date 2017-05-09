# Copyright 2017 Joachim van der Herten
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from GPflow import settings
import numpy as np
import scipy
import tensorflow as tf

float_type = settings.dtypes.float_type


class DataTransform(object):
    """
    Implements a mapping from data in domain U to domain V.
    Useful for domain scaling.
    """

    def forward(self, X):
        """
        Performs numpy transformation of U -> V
        """
        raise NotImplementedError

    def tf_forward(self, X):
        """
        Performs Tensorflow transformation of U -> V
        :param X: N x P tensor
        :return: N x Q tensor
        """
        raise NotImplementedError

    def backward(self, Y):
        """
        Performs numpy transformation of V -> U. By default, calls forward on the inverted transform object which 
        requires implementation of __invert__
        :param Y: N x Q matrix
        :return: N x P matrix
        """
        return (~self).forward(Y)

    def tf_backward(self, Y):
        """
        Performs numpy transformation of V -> U. By default, calls tf_forward on the inverted transform object which 
        requires implementation of __invert__
        :param Y: N x Q tensor
        :return: N x P tensor
                """
        return (~self).tf_forward(Y)

    def __invert__(self):
        """
        Return a DataTransform object implementing the transform from V -> U
        """
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


class LinearTransform(DataTransform):
    """
    Implements a simple linear transform of the form
    
    .. math::
       \\mathbf Y = \\mathbf X \\mathbf A + \\mathbf b

    """

    def __init__(self, A, b):
        """
        :param A: scaling matrix. Either a P-dimensional vector, or a P x P transformation matrix. For the latter, 
        the inverse and backward methods are not guaranteed to work. It is also possible to specify a matrix with size 
        P x Q with Q != P to achieve a lower dimensional representation of X. In this case, inverse and backward 
        will not work.
        :param b: A P-dimensional offset vector.
        """
        self.b = np.atleast_1d(b)
        self.A = np.atleast_1d(A)
        if len(self.A.shape) == 1:
            self.A = np.diag(self.A)

        assert (len(self.b.shape) == 1)
        assert (len(self.A.shape) == 2)

    def forward(self, X):
        return np.dot(np.atleast_2d(X), self.A) + self.b

    def backward(self, Y):
        L = scipy.linalg.cholesky(self.A)
        return scipy.linalg.cho_solve((L, False), (Y - self.b).T).T

    def tf_forward(self, X):
        return tf.matmul(X, self.A) + self.b

    def tf_backward(self, Y):
        L = tf.cholesky(self.A)
        XT = tf.matrix_triangular_solve(tf.transpose(L), tf.matrix_triangular_solve(L, tf.transpose(Y - self.b)))
        return tf.transpose(XT)

    def __invert__(self):
        A_inv = np.linalg.inv(self.A)
        return LinearTransform(A_inv, -np.dot(self.b, A_inv))

    def __str__(self):
        return 'XA + b'