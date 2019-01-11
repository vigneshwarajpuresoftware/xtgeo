# -*- coding: utf-8 -*-
"""Operations along a well, private module"""

from __future__ import print_function, absolute_import

import numpy as np
import pandas as pd

import xtgeo.cxtgeo.cxtgeo as _cxtgeo
from xtgeo.grid3d import Grid
from xtgeo.grid3d import GridProperties
from xtgeo.common import XTGeoDialog

xtg = XTGeoDialog()

logger = xtg.functionlogger(__name__)

_cxtgeo.xtg_verbose_file('NONE')
XTG_DEBUG = xtg.get_syslevel()


def rescale(self, delta=0.15):
    """Rescale by using a new MD increment

    The rescaling is technically done by interpolation in the Pandas dataframe
    """

    pdrows = pd.options.display.max_rows
    pd.options.display.max_rows = 999

    if self.mdlogname is None:
        self.geometrics()

    dfr = self._df.copy().set_index(self.mdlogname)

    logger.debug('Initial dataframe\n %s', dfr)

    start = dfr.index[0]
    stop = dfr.index[-1]

    nentry = int(round((stop - start) / delta))

    dfr = dfr.reindex(dfr.index.union(np.linspace(start, stop, num=nentry)))
    dfr = dfr.interpolate('index', limit_area='inside').loc[
        np.linspace(start, stop, num=nentry)]

    dfr[self.mdlogname] = dfr.index
    dfr.reset_index(inplace=True, drop=True)

    for lname in dfr.columns:
        if lname in self._wlogtype:
            ltype = self._wlogtype[lname]
            if ltype == 'DISC':
                dfr = dfr.round({lname: 0})

    logger.debug('Updated dataframe:\n%s', dfr)

    pd.options.display.max_rows = pdrows  # reset

    self._df = dfr


def get_ijk_from_grid(self, grid, grid_id=''):
    """Getting IJK from a grid as well logs."""

    wxarr = self.get_carray('X_UTME')
    wyarr = self.get_carray('Y_UTMN')
    wzarr = self.get_carray('Z_TVDSS')

    nlen = self.nrow
    wivec = _cxtgeo.new_intarray(nlen)
    wjvec = _cxtgeo.new_intarray(nlen)
    wkvec = _cxtgeo.new_intarray(nlen)

    onelayergrid = grid.copy()
    onelayergrid.reduce_to_one_layer()

    cstatus = _cxtgeo.grd3d_well_ijk(grid.ncol, grid.nrow, grid.nlay,
                                     grid._p_coord_v, grid._p_zcorn_v,
                                     grid._p_actnum_v,
                                     onelayergrid._p_zcorn_v,
                                     onelayergrid._p_actnum_v,
                                     self.nrow, wxarr, wyarr, wzarr,
                                     wivec, wjvec, wkvec, 0, XTG_DEBUG)

    if cstatus != 0:
        raise RuntimeError('Error from C routine, code is {}', cstatus)

    indarray = _cxtgeo.swig_carr_to_numpy_i1d(nlen, wivec).astype('float')
    jndarray = _cxtgeo.swig_carr_to_numpy_i1d(nlen, wjvec).astype('float')
    kndarray = _cxtgeo.swig_carr_to_numpy_i1d(nlen, wkvec).astype('float')

    indarray[indarray == 0] = np.nan
    jndarray[jndarray == 0] = np.nan
    kndarray[kndarray == 0] = np.nan

    icellname = 'ICELL' + grid_id
    jcellname = 'JCELL' + grid_id
    kcellname = 'KCELL' + grid_id

    self._df[icellname] = indarray
    self._df[jcellname] = jndarray
    self._df[kcellname] = kndarray

    for cellname in [icellname, jcellname, kcellname]:
        self._wlogtype[cellname] = 'DISC'

    self._wlogrecord[icellname] = {ncel: str(ncel)
                                   for ncel in range(1, grid.ncol + 1)}
    self._wlogrecord[jcellname] = {ncel: str(ncel)
                                   for ncel in range(1, grid.nrow + 1)}
    self._wlogrecord[kcellname] = {ncel: str(ncel)
                                   for ncel in range(1, grid.nlay + 1)}

    _cxtgeo.delete_intarray(wivec)
    _cxtgeo.delete_intarray(wjvec)
    _cxtgeo.delete_intarray(wkvec)
    _cxtgeo.delete_doublearray(wxarr)
    _cxtgeo.delete_doublearray(wyarr)
    _cxtgeo.delete_doublearray(wzarr)

    del onelayergrid


def get_gridproperties(self, gridprops, grid=('ICELL', 'JCELL', 'KCELL'),
                       prop_id=''):
    """Getting gridprops as logs"""

    if not isinstance(gridprops, GridProperties):
        raise ValueError('"gridprops" are not a GridProperties instance')

    if isinstance(grid, tuple):
        icl, jcl, kcl = grid
    elif isinstance(grid, Grid):
        self.get_ijk_from_grid(grid, grid_id='_tmp')
        icl, jcl, kcl = ('ICELL_tmp', 'JCELL_tmp', 'KCELL_tmp')
    else:
        raise ValueError('The "grid" is of wrong type, must be a tuple or '
                         'a Grid')
