# -*- coding: utf-8 -*-
"""Abstract baseclass for Grid and GridProperties, not to be used by itself"""

from __future__ import print_function, absolute_import

import abc
import warnings
import six

import xtgeo

xtg = xtgeo.common.XTGeoDialog()
logger = xtg.functionlogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Grid3D(object):
    """Abstract base class for Grid3D."""

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):

        self._ncol = 4
        self._nrow = 3
        self._nlay = 5

    @property
    def ncol(self):
        """ Returns the NCOL (NX or Ncolumns) number of cells"""
        return self._ncol

    @property
    def nrow(self):
        """ Returns the NROW (NY or Nrows) number of cells"""
        return self._nrow

    @property
    def nlay(self):
        """ Returns the NLAY (NZ or Nlayers) number of cells"""
        return self._nlay
