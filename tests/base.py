#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import random
from io import BytesIO
from unittest import TestCase as PythonTestCase

import numpy as np
from PIL import Image
from skimage.measure import structural_similarity

from thumbor.app import ThumborServiceApp
from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.transformer import Transformer

from tornado.testing import AsyncHTTPTestCase


class TestCase(AsyncHTTPTestCase):
    def get_app(self):
        return ThumborServiceApp(self.get_context())

    def get_context(self):
        return Context(None, Config(), None)


class FilterTestCase(PythonTestCase):
    def get_filter(self, filter_name, params_string="", config_context=None):
        config = Config(
            FILTERS=[filter_name],
        )
        importer = Importer(config)
        importer.import_modules()

        req = RequestParameters()

        context = Context(config=config, importer=importer)
        context.request = req
        context.request.engine = context.modules.engine

        if config_context is not None:
            config_context(context)

        fltr = importer.filters[0]
        fltr.pre_compile()

        context.transformer = Transformer(context)

        return fltr(params_string, context=context)

    def get_fixture_path(self, name):
        return './tests/fixtures/filters/%s' % name

    def get_fixture(self, name):
        im = Image.open(self.get_fixture_path(name))
        im = im.convert('RGBA')
        return np.array(im)

    def get_filtered(self, source_image, filter_name, params_string, config_context=None):
        fltr = self.get_filter(filter_name, params_string, config_context)
        im = Image.open(self.get_fixture_path(source_image))
        img_buffer = BytesIO()
        im.save(img_buffer, 'JPEG', quality=100)

        fltr.engine.load(img_buffer.getvalue(), '.jpg')
        fltr.context.transformer.img_operation_worker()

        fltr.run()

        fltr.engine.image = fltr.engine.image.convert('RGBA')

        return np.array(fltr.engine.image)

    def get_ssim(self, actual, expected):
        im = Image.fromarray(actual)
        im2 = Image.fromarray(expected)

        if im.size[0] != im2.size[0] or im.size[1] != im2.size[1]:
            raise RuntimeError(
                "Can't calculate SSIM for images of different sizes (one is %dx%d, the other %dx%d)." % (
                    im.size[0], im.size[1],
                    im2.size[0], im2.size[1],
                )
            )
        return structural_similarity(np.array(im), np.array(im2), multichannel=True)

    def debug(self, image):
        im = Image.fromarray(image)
        path = '/tmp/debug_image_%s.jpg' % random.randint(1, 10000)
        im.save(path, 'JPEG')
        print 'The debug image was in %s.' % path

    def debug_size(self, image):
        im = Image.fromarray(image)
        print "Image dimensions are %dx%d (shape is %s)" % (im.size[0], im.size[1], image.shape)
