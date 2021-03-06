#
# Authors: Travis Oliphant, Ed Schofield, Robert Cimrman, Nathan Bell, and others

""" Test functions for sparse matrices. Each class in the "Matrix class
based tests" section become subclasses of the classes in the "Generic
tests" section. This is done by the functions in the "Tailored base
class for generic tests" section.

"""

from __future__ import division, print_function, absolute_import

__usage__ = """
Build sparse:
  python setup.py build
Run tests if scipy is installed:
  python -c 'import scipy;scipy.sparse.test()'
Run tests if sparse is not installed:
  python tests/test_base.py
"""
from distutils.version import LooseVersion

import warnings

import numpy as np
from scipy.lib.six import xrange
from numpy import arange, zeros, array, dot, matrix, asmatrix, asarray, \
                  vstack, ndarray, transpose, diag, kron, inf, conjugate, \
                  int8, ComplexWarning

import random
from numpy.testing import assert_raises, assert_equal, assert_array_equal, \
        assert_array_almost_equal, assert_almost_equal, assert_, \
        dec, run_module_suite, assert_allclose

import scipy.linalg

import scipy.sparse as sparse
from scipy.sparse import csc_matrix, csr_matrix, dok_matrix, \
        coo_matrix, lil_matrix, dia_matrix, bsr_matrix, \
        eye, isspmatrix, SparseEfficiencyWarning
from scipy.sparse.sputils import supported_dtypes, isscalarlike
from scipy.sparse.linalg import splu, expm, inv

import nose

warnings.simplefilter('ignore', SparseEfficiencyWarning)
warnings.simplefilter('ignore', ComplexWarning)


def _can_cast_samekind(dtype1, dtype2):
    """Compatibility function for numpy 1.5.1; `casting` kw is numpy >=1.6.x

    default for casting kw is 'safe', which gives the same result as in 1.5.x
    and a strict subset of 'same_kind'.  So for 1.5.x we just skip the cases
    where 'safe' is False and 'same_kind' True.
    """
    if np.__version__[:3] == '1.5':
        return np.can_cast(dtype1, dtype2)
    else:
        return np.can_cast(dtype1, dtype2, casting='same_kind')


def todense(a):
    if isinstance(a, np.ndarray) or isscalarlike(a):
        return a
    return a.todense()


class MultipliesWithMatrix(object):
    """Class that knows how to multiply with a sparse matrix."""

    def __mul__(self, other):
        return "matrix on the right"

    def __rmul__(self, other):
        return "matrix on the left"


#------------------------------------------------------------------------------
# Generic tests
#------------------------------------------------------------------------------


# TODO check that spmatrix( ... , copy=X ) is respected
# TODO test prune
# TODO test has_sorted_indices
class _TestCommon:
    """test common functionality shared by all sparse formats"""
    checked_dtypes = supported_dtypes

    def __init__(self):
        # Cannonical data.
        self.dat = matrix([[1,0,0,2],[3,0,1,0],[0,2,0,0]],'d')
        self.datsp = self.spmatrix(self.dat)

        # Some sparse and dense matrices with data for every supported
        # dtype.
        self.dat_dtypes = {}
        self.datsp_dtypes = {}
        for dtype in self.checked_dtypes:
            self.dat_dtypes[dtype] = self.dat.astype(dtype)
            self.datsp_dtypes[dtype] = self.spmatrix(self.dat.astype(dtype))

        # Check that the original data is equivalent to the
        # corresponding dat_dtypes & datsp_dtypes.
        assert_equal(self.dat, self.dat_dtypes[np.float64])
        assert_equal(self.datsp.todense(),
                     self.datsp_dtypes[np.float64].todense())

    def test_bool(self):
        def check(dtype):
            datsp = self.datsp_dtypes[dtype]

            assert_raises(ValueError, bool, datsp)
            assert_(self.spmatrix([1]))
            assert_(not self.spmatrix([0]))
        for dtype in self.checked_dtypes:
            fails = self.__class__ == TestDOK
            msg = "Cannot create a rank <= 2 DOK matrix."
            yield dec.skipif(fails, msg)(check), dtype

    def test_bool_rollover(self):
        # bool's underlying dtype is 1 byte, check that it does not
        # rollover True -> False at 256.
        dat = np.matrix([[True, False]])
        datsp = self.spmatrix(dat)

        for _ in range(10):
            datsp = datsp + datsp
            dat = dat + dat
        assert_array_equal(dat, datsp.todense())

    def test_eq(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datbsr = bsr_matrix(dat)
            datcsr = csr_matrix(dat)
            datcsc = csc_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat == dat2, (datsp == datsp2).todense())
            # mix sparse types
            assert_array_equal(dat == dat2, (datbsr == datsp2).todense())
            assert_array_equal(dat == dat2, (datcsr == datsp2).todense())
            assert_array_equal(dat == dat2, (datcsc == datsp2).todense())
            assert_array_equal(dat == dat2, (datlil == datsp2).todense())
            # sparse/dense
            assert_array_equal(dat == datsp2, datsp2 == dat)
            # sparse/scalar
            assert_array_equal(dat == 0, (datsp == 0).todense())
            assert_array_equal(dat == 1, (datsp == 1).todense())

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

    def test_ne(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datbsr = bsr_matrix(dat)
            datcsc = csc_matrix(dat)
            datcsr = csr_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat != dat2, (datsp != datsp2).todense())
            # mix sparse types
            assert_array_equal(dat != dat2, (datbsr != datsp2).todense())
            assert_array_equal(dat != dat2, (datcsc != datsp2).todense())
            assert_array_equal(dat != dat2, (datcsr != datsp2).todense())
            assert_array_equal(dat != dat2, (datlil != datsp2).todense())
            # sparse/dense
            assert_array_equal(dat != datsp2, datsp2 != dat)
            # sparse/scalar
            assert_array_equal(dat != 0, (datsp != 0).todense())
            assert_array_equal(dat != 1, (datsp != 1).todense())
            assert_array_equal(0 != dat, (0 != datsp).todense())
            assert_array_equal(1 != dat, (1 != datsp).todense())

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

    def test_lt(self):
        def check(dtype):
            # data
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datcomplex = dat.astype(np.complex)
            datcomplex[:,0] = 1 + 1j
            datspcomplex = self.spmatrix(datcomplex)
            datbsr = bsr_matrix(dat)
            datcsc = csc_matrix(dat)
            datcsr = csr_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat < dat2, (datsp < datsp2).todense())
            assert_array_equal(datcomplex < dat2, (datspcomplex < datsp2).todense())
            # mix sparse types
            assert_array_equal(dat < dat2, (datbsr < datsp2).todense())
            assert_array_equal(dat < dat2, (datcsc < datsp2).todense())
            assert_array_equal(dat < dat2, (datcsr < datsp2).todense())
            assert_array_equal(dat < dat2, (datlil < datsp2).todense())

            assert_array_equal(dat2 < dat, (datsp2 < datbsr).todense())
            assert_array_equal(dat2 < dat, (datsp2 < datcsc).todense())
            assert_array_equal(dat2 < dat, (datsp2 < datcsr).todense())
            assert_array_equal(dat2 < dat, (datsp2 < datlil).todense())
            # sparse/dense
            assert_array_equal(dat < dat2, datsp < dat2)
            assert_array_equal(datcomplex < dat2, datspcomplex < dat2)
            # sparse/scalar
            assert_array_equal((datsp < 2).todense(), dat < 2)
            assert_array_equal((datsp < 1).todense(), dat < 1)
            assert_array_equal((datsp < 0).todense(), dat < 0)
            assert_array_equal((datsp < -1).todense(), dat < -1)
            assert_array_equal((datsp < -2).todense(), dat < -2)

            assert_array_equal((2 < datsp).todense(), 2 < dat)
            assert_array_equal((1 < datsp).todense(), 1 < dat)
            assert_array_equal((0 < datsp).todense(), 0 < dat)
            assert_array_equal((-1 < datsp).todense(), -1 < dat)
            assert_array_equal((-2 < datsp).todense(), -2 < dat)

        def check_fail(dtype):
            # data
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)

            # dense rhs fails
            assert_array_equal(dat < datsp2, datsp < dat2)

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

        msg = "Dense rhs is not supported for inequalities."
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.knownfailureif(True, msg)(check_fail), dtype

    def test_gt(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datcomplex = dat.astype(np.complex)
            datcomplex[:,0] = 1 + 1j
            datspcomplex = self.spmatrix(datcomplex)
            datbsr = bsr_matrix(dat)
            datcsc = csc_matrix(dat)
            datcsr = csr_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat > dat2, (datsp > datsp2).todense())
            assert_array_equal(datcomplex > dat2, (datspcomplex > datsp2).todense())
            # mix sparse types
            assert_array_equal(dat > dat2, (datbsr > datsp2).todense())
            assert_array_equal(dat > dat2, (datcsc > datsp2).todense())
            assert_array_equal(dat > dat2, (datcsr > datsp2).todense())
            assert_array_equal(dat > dat2, (datlil > datsp2).todense())

            assert_array_equal(dat2 > dat, (datsp2 > datbsr).todense())
            assert_array_equal(dat2 > dat, (datsp2 > datcsc).todense())
            assert_array_equal(dat2 > dat, (datsp2 > datcsr).todense())
            assert_array_equal(dat2 > dat, (datsp2 > datlil).todense())
            # sparse/dense
            assert_array_equal(dat > dat2, datsp > dat2)
            assert_array_equal(datcomplex > dat2, datspcomplex > dat2)
            # sparse/scalar
            assert_array_equal((datsp > 2).todense(), dat > 2)
            assert_array_equal((datsp > 1).todense(), dat > 1)
            assert_array_equal((datsp > 0).todense(), dat > 0)
            assert_array_equal((datsp > -1).todense(), dat > -1)
            assert_array_equal((datsp > -2).todense(), dat > -2)

            assert_array_equal((2 > datsp).todense(), 2 > dat)
            assert_array_equal((1 > datsp).todense(), 1 > dat)
            assert_array_equal((0 > datsp).todense(), 0 > dat)
            assert_array_equal((-1 > datsp).todense(), -1 > dat)
            assert_array_equal((-2 > datsp).todense(), -2 > dat)

        def check_fail(dtype):
            # data
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)

            # dense rhs fails
            assert_array_equal(dat > datsp2, datsp > dat2)

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

        msg = "Dense rhs is not supported for inequalities."
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.knownfailureif(True, msg)(check_fail), dtype

    def test_le(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datcomplex = dat.astype(np.complex)
            datcomplex[:,0] = 1 + 1j
            datspcomplex = self.spmatrix(datcomplex)
            datbsr = bsr_matrix(dat)
            datcsc = csc_matrix(dat)
            datcsr = csr_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat <= dat2, (datsp <= datsp2).todense())
            assert_array_equal(datcomplex <= dat2, (datspcomplex <= datsp2).todense())
            # mix sparse types
            assert_array_equal((datbsr <= datsp2).todense(), dat <= dat2)
            assert_array_equal((datcsc <= datsp2).todense(), dat <= dat2)
            assert_array_equal((datcsr <= datsp2).todense(), dat <= dat2)
            assert_array_equal((datlil <= datsp2).todense(), dat <= dat2)

            assert_array_equal((datsp2 <= datbsr).todense(), dat2 <= dat)
            assert_array_equal((datsp2 <= datcsc).todense(), dat2 <= dat)
            assert_array_equal((datsp2 <= datcsr).todense(), dat2 <= dat)
            assert_array_equal((datsp2 <= datlil).todense(), dat2 <= dat)
            # sparse/dense
            assert_array_equal(datsp <= dat2, dat <= dat2)
            assert_array_equal(datspcomplex <= dat2, datcomplex <= dat2)
            # sparse/scalar
            assert_array_equal((datsp <= 2).todense(), dat <= 2)
            assert_array_equal((datsp <= 1).todense(), dat <= 1)
            assert_array_equal((datsp <= -1).todense(), dat <= -1)
            assert_array_equal((datsp <= -2).todense(), dat <= -2)

            assert_array_equal((2 <= datsp).todense(), 2 <= dat)
            assert_array_equal((1 <= datsp).todense(), 1 <= dat)
            assert_array_equal((-1 <= datsp).todense(), -1 <= dat)
            assert_array_equal((-2 <= datsp).todense(), -2 <= dat)

        def check_fail(dtype):
            # data
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)

            # dense rhs fails
            assert_array_equal(dat <= datsp2, datsp <= dat2)

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

        msg = "Dense rhs is not supported for inequalities."
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.knownfailureif(True, msg)(check_fail), dtype

    def test_ge(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)
            datcomplex = dat.astype(np.complex)
            datcomplex[:,0] = 1 + 1j
            datspcomplex = self.spmatrix(datcomplex)
            datbsr = bsr_matrix(dat)
            datcsc = csc_matrix(dat)
            datcsr = csr_matrix(dat)
            datlil = lil_matrix(dat)

            # sparse/sparse
            assert_array_equal(dat >= dat2, (datsp >= datsp2).todense())
            assert_array_equal(datcomplex >= dat2, (datspcomplex >= datsp2).todense())
            # mix sparse types
            # mix sparse types
            assert_array_equal((datbsr >= datsp2).todense(), dat >= dat2)
            assert_array_equal((datcsc >= datsp2).todense(), dat >= dat2)
            assert_array_equal((datcsr >= datsp2).todense(), dat >= dat2)
            assert_array_equal((datlil >= datsp2).todense(), dat >= dat2)

            assert_array_equal((datsp2 >= datbsr).todense(), dat2 >= dat)
            assert_array_equal((datsp2 >= datcsc).todense(), dat2 >= dat)
            assert_array_equal((datsp2 >= datcsr).todense(), dat2 >= dat)
            assert_array_equal((datsp2 >= datlil).todense(), dat2 >= dat)
            # sparse/dense
            assert_array_equal(datsp >= dat2, dat >= dat2)
            assert_array_equal(datspcomplex >= dat2, datcomplex >= dat2)
            # sparse/scalar
            assert_array_equal((datsp >= 2).todense(), dat >= 2)
            assert_array_equal((datsp >= 1).todense(), dat >= 1)
            assert_array_equal((datsp >= -1).todense(), dat >= -1)
            assert_array_equal((datsp >= -2).todense(), dat >= -2)

            assert_array_equal((2 >= datsp).todense(), 2 >= dat)
            assert_array_equal((1 >= datsp).todense(), 1 >= dat)
            assert_array_equal((-1 >= datsp).todense(), -1 >= dat)
            assert_array_equal((-2 >= datsp).todense(), -2 >= dat)

        def check_fail(dtype):
            # data
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]
            dat2 = dat.copy()
            dat2[:,0] = 0
            datsp2 = self.spmatrix(dat2)

            # dense rhs fails
            assert_array_equal(dat >= datsp2, datsp >= dat2)

        msg = "Bool comparisons only implemented for BSR, CSC, and CSR."
        fails = not (self.__class__ == TestBSR or self.__class__ == TestCSC or
                     self.__class__ == TestCSR)
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.skipif(fails, msg)(check), dtype

        msg = "Dense rhs is not supported for inequalities."
        for dtype in self.checked_dtypes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=np.ComplexWarning)
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield dec.knownfailureif(True, msg)(check_fail), dtype

    def test_empty(self):
        # create empty matrices
        assert_equal(self.spmatrix((3,3)).todense(), np.zeros((3,3)))
        assert_equal(self.spmatrix((3,3)).nnz, 0)

    def test_invalid_shapes(self):
        assert_raises(ValueError, self.spmatrix, (-1,3))
        assert_raises(ValueError, self.spmatrix, (3,-1))
        assert_raises(ValueError, self.spmatrix, (-1,-1))

    def test_repr(self):
        repr(self.datsp)

    def test_str(self):
        str(self.datsp)

    def test_empty_arithmetic(self):
        # Test manipulating empty matrices. Fails in SciPy SVN <= r1768
        shape = (5, 5)
        for mytype in [np.dtype('int32'), np.dtype('float32'),
                np.dtype('float64'), np.dtype('complex64'),
                np.dtype('complex128')]:
            a = self.spmatrix(shape, dtype=mytype)
            b = a + a
            c = 2 * a
            d = a * a.tocsc()
            e = a * a.tocsr()
            f = a * a.tocoo()
            for m in [a,b,c,d,e,f]:
                assert_equal(m.A, a.A*a.A)
                # These fail in all revisions <= r1768:
                assert_equal(m.dtype,mytype)
                assert_equal(m.A.dtype,mytype)

    def test_abs(self):
        A = matrix([[-1, 0, 17],[0, -5, 0],[1, -4, 0],[0,0,0]],'d')
        assert_equal(abs(A),abs(self.spmatrix(A)).todense())

    def test_neg(self):
        A = matrix([[-1, 0, 17],[0, -5, 0],[1, -4, 0],[0,0,0]],'d')
        assert_equal(-A,(-self.spmatrix(A)).todense())

    def test_real(self):
        D = matrix([[1 + 3j, 2 - 4j]])
        A = self.spmatrix(D)
        assert_equal(A.real.todense(),D.real)

    def test_imag(self):
        D = matrix([[1 + 3j, 2 - 4j]])
        A = self.spmatrix(D)
        assert_equal(A.imag.todense(),D.imag)

    def test_diagonal(self):
        # Does the matrix's .diagonal() method work?
        mats = []
        mats.append([[1,0,2]])
        mats.append([[1],[0],[2]])
        mats.append([[0,1],[0,2],[0,3]])
        mats.append([[0,0,1],[0,0,2],[0,3,0]])

        mats.append(kron(mats[0],[[1,2]]))
        mats.append(kron(mats[0],[[1],[2]]))
        mats.append(kron(mats[1],[[1,2],[3,4]]))
        mats.append(kron(mats[2],[[1,2],[3,4]]))
        mats.append(kron(mats[3],[[1,2],[3,4]]))
        mats.append(kron(mats[3],[[1,2,3,4]]))

        for m in mats:
            assert_equal(self.spmatrix(m).diagonal(),diag(m))

    def test_nonzero(self):
        A = array([[1, 0, 1],[0, 1, 1],[0, 0, 1]])
        Asp = self.spmatrix(A)

        A_nz = set([tuple(ij) for ij in transpose(A.nonzero())])
        Asp_nz = set([tuple(ij) for ij in transpose(Asp.nonzero())])

        assert_equal(A_nz, Asp_nz)

    def test_getrow(self):
        assert_array_equal(self.datsp.getrow(1).todense(), self.dat[1,:])
        assert_array_equal(self.datsp.getrow(-1).todense(), self.dat[-1,:])

    def test_getcol(self):
        assert_array_equal(self.datsp.getcol(1).todense(), self.dat[:,1])
        assert_array_equal(self.datsp.getcol(-1).todense(), self.dat[:,-1])

    def test_sum(self):
        def check(dtype):
            dat = np.matrix([[0, 1, 2],
                            [3, -4, 5],
                            [-6, 7, 9]], dtype=dtype)
            datsp = self.spmatrix(dat, dtype=dtype)

            # Does the matrix's .sum(axis=...) method work?
            assert_array_almost_equal(dat.sum(), datsp.sum())
            assert_equal(dat.sum().dtype, datsp.sum().dtype)
            assert_array_almost_equal(dat.sum(axis=None), datsp.sum(axis=None))
            assert_equal(dat.sum(axis=None).dtype, datsp.sum(axis=None).dtype)
            assert_array_almost_equal(dat.sum(axis=0), datsp.sum(axis=0))
            assert_equal(dat.sum(axis=0).dtype, datsp.sum(axis=0).dtype)
            assert_array_almost_equal(dat.sum(axis=1), datsp.sum(axis=1))
            assert_equal(dat.sum(axis=1).dtype, datsp.sum(axis=1).dtype)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_mean(self):
        def check(dtype):
            dat = np.matrix([[0, 1, 2],
                            [3, -4, 5],
                            [-6, 7, 9]], dtype=dtype)
            datsp = self.spmatrix(dat, dtype=dtype)

            # Does the matrix's .mean(axis=...) method work?
            assert_array_almost_equal(dat.mean(), datsp.mean())
            assert_equal(dat.mean().dtype, datsp.mean().dtype)
            assert_array_almost_equal(dat.mean(axis=None), datsp.mean(axis=None))
            assert_equal(dat.mean(axis=None).dtype, datsp.mean(axis=None).dtype)
            assert_array_almost_equal(dat.mean(axis=0), datsp.mean(axis=0))
            assert_equal(dat.mean(axis=0).dtype, datsp.mean(axis=0).dtype)
            assert_array_almost_equal(dat.mean(axis=1), datsp.mean(axis=1))
            assert_equal(dat.mean(axis=1).dtype, datsp.mean(axis=1).dtype)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_expm(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)

            M = array([[1, 0, 2], [0, 0, 3], [-4, 5, 6]], float)
            sM = self.spmatrix(M, shape=(3,3), dtype=float)
            Mexp = scipy.linalg.expm(M)
            sMexp = expm(sM).todense()
            assert_array_almost_equal((sMexp - Mexp), zeros((3, 3)))

            N = array([[3., 0., 1.], [0., 2., 0.], [0., 0., 0.]])
            sN = self.spmatrix(N, shape=(3,3), dtype=float)
            Nexp = scipy.linalg.expm(N)
            sNexp = expm(sN).todense()
            assert_array_almost_equal((sNexp - Nexp), zeros((3, 3)))

    def test_inv(self):
        def check(dtype):
            M = array([[1, 0, 2], [0, 0, 3], [-4, 5, 6]], dtype)
            sM = self.spmatrix(M, shape=(3,3), dtype=dtype)
            sMinv = inv(sM)
            assert_array_almost_equal(sMinv.dot(sM).todense(), np.eye(3))
        for dtype in [float]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                yield check, dtype

    def test_from_array(self):
        A = array([[1,0,0],[2,3,4],[0,5,0],[0,0,0]])
        assert_array_equal(self.spmatrix(A).toarray(), A)

        A = array([[1.0 + 3j, 0, 0],
                   [0, 2.0 + 5, 0],
                   [0, 0, 0]])
        assert_array_equal(self.spmatrix(A).toarray(), A)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=np.ComplexWarning)
            assert_array_equal(self.spmatrix(A, dtype='int16').toarray(), A.astype('int16'))

    def test_from_matrix(self):
        A = matrix([[1,0,0],[2,3,4],[0,5,0],[0,0,0]])
        assert_array_equal(self.spmatrix(A).todense(), A)

        A = matrix([[1.0 + 3j, 0, 0],
                    [0, 2.0 + 5, 0],
                    [0, 0, 0]])
        assert_array_equal(self.spmatrix(A).toarray(), A)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=np.ComplexWarning)
            assert_array_equal(self.spmatrix(A, dtype='int16').toarray(), A.astype('int16'))

    def test_from_list(self):
        A = [[1,0,0],[2,3,4],[0,5,0],[0,0,0]]
        assert_array_equal(self.spmatrix(A).todense(), A)

        A = [[1.0 + 3j, 0, 0],
             [0, 2.0 + 5, 0],
             [0, 0, 0]]
        assert_array_equal(self.spmatrix(A).toarray(), array(A))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=np.ComplexWarning)
            assert_array_equal(self.spmatrix(A, dtype='int16').todense(), array(A).astype('int16'))

    def test_from_sparse(self):
        D = array([[1,0,0],[2,3,4],[0,5,0],[0,0,0]])
        S = csr_matrix(D)
        assert_array_equal(self.spmatrix(S).toarray(), D)
        S = self.spmatrix(D)
        assert_array_equal(self.spmatrix(S).toarray(), D)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=np.ComplexWarning)
            D = array([[1.0 + 3j, 0, 0],
                       [0, 2.0 + 5, 0],
                       [0, 0, 0]])
            S = csr_matrix(D)
            assert_array_equal(self.spmatrix(S).toarray(), D)
            assert_array_equal(self.spmatrix(S, dtype='int16').toarray(), D.astype('int16'))
            S = self.spmatrix(D)
            assert_array_equal(self.spmatrix(S).toarray(), D)
            assert_array_equal(self.spmatrix(S, dtype='int16').toarray(), D.astype('int16'))

    # def test_array(self):
    #    """test array(A) where A is in sparse format"""
    #    assert_equal( array(self.datsp), self.dat )

    def test_todense(self):
        # Check C-contiguous (default).
        chk = self.datsp.todense()
        assert_array_equal(chk, self.dat)
        assert_(chk.flags.c_contiguous)
        assert_(not chk.flags.f_contiguous)
        # Check C-contiguous (with arg).
        chk = self.datsp.todense(order='C')
        assert_array_equal(chk, self.dat)
        assert_(chk.flags.c_contiguous)
        assert_(not chk.flags.f_contiguous)
        # Check F-contiguous (with arg).
        chk = self.datsp.todense(order='F')
        assert_array_equal(chk, self.dat)
        assert_(not chk.flags.c_contiguous)
        assert_(chk.flags.f_contiguous)
        # Check with out argument (array).
        out = np.zeros(self.datsp.shape, dtype=self.datsp.dtype)
        chk = self.datsp.todense(out=out)
        assert_array_equal(self.dat, out)
        assert_array_equal(self.dat, chk)
        assert_(chk.base is out)
        # Check with out array (matrix).
        out = np.asmatrix(np.zeros(self.datsp.shape, dtype=self.datsp.dtype))
        chk = self.datsp.todense(out=out)
        assert_array_equal(self.dat, out)
        assert_array_equal(self.dat, chk)
        assert_(chk is out)
        a = matrix([1.,2.,3.])
        dense_dot_dense = a * self.dat
        check = a * self.datsp.todense()
        assert_array_equal(dense_dot_dense, check)
        b = matrix([1.,2.,3.,4.]).T
        dense_dot_dense = self.dat * b
        check2 = self.datsp.todense() * b
        assert_array_equal(dense_dot_dense, check2)
        # Check bool data works.
        spbool = self.spmatrix(self.dat, dtype=bool)
        matbool = self.dat.astype(bool)
        assert_array_equal(spbool.todense(), matbool)

    def test_toarray(self):
        # Check C-contiguous (default).
        dat = asarray(self.dat)
        chk = self.datsp.toarray()
        assert_array_equal(chk, dat)
        assert_(chk.flags.c_contiguous)
        assert_(not chk.flags.f_contiguous)
        # Check C-contiguous (with arg).
        chk = self.datsp.toarray(order='C')
        assert_array_equal(chk, dat)
        assert_(chk.flags.c_contiguous)
        assert_(not chk.flags.f_contiguous)
        # Check F-contiguous (with arg).
        chk = self.datsp.toarray(order='F')
        assert_array_equal(chk, dat)
        assert_(not chk.flags.c_contiguous)
        assert_(chk.flags.f_contiguous)
        # Check with output arg.
        out = np.zeros(self.datsp.shape, dtype=self.datsp.dtype)
        self.datsp.toarray(out=out)
        assert_array_equal(chk, dat)
        # Check that things are fine when we don't initialize with zeros.
        out[...] = 1.
        self.datsp.toarray(out=out)
        assert_array_equal(chk, dat)
        a = array([1.,2.,3.])
        dense_dot_dense = dot(a, dat)
        check = dot(a, self.datsp.toarray())
        assert_array_equal(dense_dot_dense, check)
        b = array([1.,2.,3.,4.])
        dense_dot_dense = dot(dat, b)
        check2 = dot(self.datsp.toarray(), b)
        assert_array_equal(dense_dot_dense, check2)
        # Check bool data works.
        spbool = self.spmatrix(self.dat, dtype=bool)
        arrbool = dat.astype(bool)
        assert_array_equal(spbool.toarray(), arrbool)

    def test_astype(self):
        D = array([[1.0 + 3j, 0, 0],
                   [0, 2.0 + 5, 0],
                   [0, 0, 0]])
        S = self.spmatrix(D)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=np.ComplexWarning)

            for x in supported_dtypes:
                assert_equal(S.astype(x).dtype, D.astype(x).dtype)  # correct type
                assert_equal(S.astype(x).toarray(), D.astype(x))        # correct values
                assert_equal(S.astype(x).format, S.format)           # format preserved

    def test_asfptype(self):
        A = self.spmatrix(arange(6,dtype='int32').reshape(2,3))

        assert_equal(A.dtype, np.dtype('int32'))
        assert_equal(A.asfptype().dtype, np.dtype('float64'))
        assert_equal(A.asfptype().format, A.format)
        assert_equal(A.astype('int16').asfptype().dtype, np.dtype('float32'))
        assert_equal(A.astype('complex128').asfptype().dtype, np.dtype('complex128'))

        B = A.asfptype()
        C = B.asfptype()
        assert_(B is C)

    def test_mul_scalar(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            assert_array_equal(dat*2,(datsp*2).todense())
            assert_array_equal(dat*17.3,(datsp*17.3).todense())

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_rmul_scalar(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            assert_array_equal(2*dat,(2*datsp).todense())
            assert_array_equal(17.3*dat,(17.3*datsp).todense())

        for dtype in self.checked_dtypes:
            fails = ((dtype == np.typeDict['int']) and
                    (self.__class__ == TestLIL or
                     self.__class__ == TestDOK))
            msg = "LIL and DOK type's __rmul__ method has problems with int data."
            yield dec.knownfailureif(fails, msg)(check), dtype

    def test_add(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            a = dat.copy()
            a[0,2] = 2.0
            b = datsp
            c = b + a
            assert_array_equal(c, b.todense() + a)

            c = b + b.tocsr()
            assert_array_equal(c.todense(),
                               b.todense() + b.todense())

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_radd(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            a = dat.copy()
            a[0,2] = 2.0
            b = datsp
            c = a + b
            assert_array_equal(c, a + b.todense())

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_sub(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            assert_array_equal((datsp - datsp).todense(),[[0,0,0,0],[0,0,0,0],[0,0,0,0]])

            A = self.spmatrix(matrix([[1,0,0,4],[-1,0,0,0],[0,8,0,-5]],'d'))
            assert_array_equal((datsp - A).todense(),dat - A.todense())
            assert_array_equal((A - datsp).todense(),A.todense() - dat)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_rsub(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            assert_array_equal((dat - datsp),[[0,0,0,0],[0,0,0,0],[0,0,0,0]])
            assert_array_equal((datsp - dat),[[0,0,0,0],[0,0,0,0],[0,0,0,0]])

            A = self.spmatrix(matrix([[1,0,0,4],[-1,0,0,0],[0,8,0,-5]],'d'))
            assert_array_equal((dat - A),dat - A.todense())
            assert_array_equal((A - dat),A.todense() - dat)
            assert_array_equal(A.todense() - datsp,A.todense() - dat)
            assert_array_equal(datsp - A.todense(),dat - A.todense())

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_add0(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            # Adding 0 to a sparse matrix
            assert_array_equal((datsp + 0).todense(), dat)
            # use sum (which takes 0 as a starting value)
            sumS = sum([k * datsp for k in range(1, 3)])
            sumD = sum([k * dat for k in range(1, 3)])
            assert_almost_equal(sumS.todense(), sumD)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_elementwise_multiply(self):
        # real/real
        A = array([[4,0,9],[2,-3,5]])
        B = array([[0,7,0],[0,-4,0]])
        Asp = self.spmatrix(A)
        Bsp = self.spmatrix(B)
        assert_almost_equal(Asp.multiply(Bsp).todense(), A*B)  # sparse/sparse
        assert_almost_equal(Asp.multiply(B), A*B)  # sparse/dense

        # complex/complex
        C = array([[1-2j,0+5j,-1+0j],[4-3j,-3+6j,5]])
        D = array([[5+2j,7-3j,-2+1j],[0-1j,-4+2j,9]])
        Csp = self.spmatrix(C)
        Dsp = self.spmatrix(D)
        assert_almost_equal(Csp.multiply(Dsp).todense(), C*D)  # sparse/sparse
        assert_almost_equal(Csp.multiply(D), C*D)  # sparse/dense

        # real/complex
        assert_almost_equal(Asp.multiply(Dsp).todense(), A*D)  # sparse/sparse
        assert_almost_equal(Asp.multiply(D), A*D)  # sparse/dense

    def test_elementwise_multiply_broadcast(self):
        A = array([4])
        B = array([[-9]])
        C = array([1,-1,0])
        D = array([[7,9,-9]])
        E = array([[3],[2],[1]])
        F = array([[8,6,3],[-4,3,2],[6,6,6]])
        G = [1, 2, 3]
        H = np.ones((3, 4))
        J = H.T

        # Rank 1 arrays can't be cast as spmatrices (A and C) so leave
        # them out.
        Bsp = self.spmatrix(B)
        Dsp = self.spmatrix(D)
        Esp = self.spmatrix(E)
        Fsp = self.spmatrix(F)
        Hsp = self.spmatrix(H)
        Hspp = self.spmatrix(H[0,None])
        Jsp = self.spmatrix(J)
        Jspp = self.spmatrix(J[:,0,None])

        matrices = [A, B, C, D, E, F, G, H, J]
        spmatrices = [Bsp, Dsp, Esp, Fsp, Hsp, Hspp, Jsp, Jspp]

        # sparse/sparse
        for i in spmatrices:
            for j in spmatrices:
                try:
                    dense_mult = np.multiply(i.todense(), j.todense())
                except ValueError:
                    assert_raises(ValueError, i.multiply, j)
                    continue
                sp_mult = i.multiply(j)
                if isspmatrix(sp_mult):
                    assert_almost_equal(sp_mult.todense(), dense_mult)
                else:
                    assert_almost_equal(sp_mult, dense_mult)

        # sparse/dense
        for i in spmatrices:
            for j in matrices:
                try:
                    dense_mult = np.multiply(i.todense(), j)
                except ValueError:
                    assert_raises(ValueError, i.multiply, j)
                    continue
                sp_mult = i.multiply(j)
                if isspmatrix(sp_mult):
                    assert_almost_equal(sp_mult.todense(), dense_mult)
                else:
                    assert_almost_equal(sp_mult, dense_mult)

    def test_elementwise_divide(self):
        expected = [[1,np.nan,np.nan,1],[1,np.nan,1,np.nan],[np.nan,1,np.nan,np.nan]]
        assert_array_equal(todense(self.datsp / self.datsp),expected)

        denom = self.spmatrix(matrix([[1,0,0,4],[-1,0,0,0],[0,8,0,-5]],'d'))
        res = matrix([[1,np.nan,np.nan,0.5],[-3,np.nan,inf,np.nan],[np.nan,0.25,np.nan,np.nan]],'d')
        assert_array_equal(todense(self.datsp / denom),res)

        # complex
        A = array([[1-2j,0+5j,-1+0j],[4-3j,-3+6j,5]])
        B = array([[5+2j,7-3j,-2+1j],[0-1j,-4+2j,9]])
        Asp = self.spmatrix(A)
        Bsp = self.spmatrix(B)
        assert_almost_equal(todense(Asp / Bsp), A/B)

    def test_pow(self):
        A = matrix([[1,0,2,0],[0,3,4,0],[0,5,0,0],[0,6,7,8]])
        B = self.spmatrix(A)

        for exponent in [0,1,2,3]:
            assert_array_equal((B**exponent).todense(),A**exponent)

        # invalid exponents
        for exponent in [-1, 2.2, 1 + 3j]:
            assert_raises(Exception, B.__pow__, exponent)

        # nonsquare matrix
        B = self.spmatrix(A[:3,:])
        assert_raises(Exception, B.__pow__, 1)

    def test_rmatvec(self):
        M = self.spmatrix(matrix([[3,0,0],[0,1,0],[2,0,3.0],[2,3,0]]))
        assert_array_almost_equal([1,2,3,4]*M, dot([1,2,3,4], M.toarray()))
        row = matrix([[1,2,3,4]])
        assert_array_almost_equal(row*M, row*M.todense())

    def test_small_multiplication(self):
        # test that A*x works for x with shape () (1,) and (1,1)
        A = self.spmatrix([[1],[2],[3]])

        assert_(isspmatrix(A * array(1)))
        assert_equal((A * array(1)).todense(), [[1],[2],[3]])
        assert_equal(A * array([1]), array([1,2,3]))
        assert_equal(A * array([[1]]), array([[1],[2],[3]]))

    def test_multiply_custom(self):
        A = self.spmatrix([[1], [2], [3]])
        B = MultipliesWithMatrix()
        assert_equal(A * B, "matrix on the left")
        assert_equal(B * A, "matrix on the right")

    def test_matvec(self):
        M = self.spmatrix(matrix([[3,0,0],[0,1,0],[2,0,3.0],[2,3,0]]))
        col = matrix([1,2,3]).T
        assert_array_almost_equal(M * col, M.todense() * col)

        # check result dimensions (ticket #514)
        assert_equal((M * array([1,2,3])).shape,(4,))
        assert_equal((M * array([[1],[2],[3]])).shape,(4,1))
        assert_equal((M * matrix([[1],[2],[3]])).shape,(4,1))

        # check result type
        assert_(isinstance(M * array([1,2,3]), ndarray))
        assert_(isinstance(M * matrix([1,2,3]).T, matrix))

        # ensure exception is raised for improper dimensions
        bad_vecs = [array([1,2]), array([1,2,3,4]), array([[1],[2]]),
                    matrix([1,2,3]), matrix([[1],[2]])]
        for x in bad_vecs:
            assert_raises(ValueError, M.__mul__, x)

        # Should this be supported or not?!
        # flat = array([1,2,3])
        # assert_array_almost_equal(M*flat, M.todense()*flat)
        # Currently numpy dense matrices promote the result to a 1x3 matrix,
        # whereas sparse matrices leave the result as a rank-1 array.  Which
        # is preferable?

        # Note: the following command does not work.  Both NumPy matrices
        # and spmatrices should raise exceptions!
        # assert_array_almost_equal(M*[1,2,3], M.todense()*[1,2,3])

        # The current relationship between sparse matrix products and array
        # products is as follows:
        assert_array_almost_equal(M*array([1,2,3]), dot(M.A,[1,2,3]))
        assert_array_almost_equal(M*[[1],[2],[3]], asmatrix(dot(M.A,[1,2,3])).T)
        # Note that the result of M * x is dense if x has a singleton dimension.

        # Currently M.matvec(asarray(col)) is rank-1, whereas M.matvec(col)
        # is rank-2.  Is this desirable?

    def test_matmat_sparse(self):
        a = matrix([[3,0,0],[0,1,0],[2,0,3.0],[2,3,0]])
        a2 = array([[3,0,0],[0,1,0],[2,0,3.0],[2,3,0]])
        b = matrix([[0,1],[1,0],[0,2]],'d')
        asp = self.spmatrix(a)
        bsp = self.spmatrix(b)
        assert_array_almost_equal((asp*bsp).todense(), a*b)
        assert_array_almost_equal(asp*b, a*b)
        assert_array_almost_equal(a*bsp, a*b)
        assert_array_almost_equal(a2*bsp, a*b)

        # Now try performing cross-type multplication:
        csp = bsp.tocsc()
        c = b
        assert_array_almost_equal((asp*csp).todense(), a*c)
        assert_array_almost_equal(asp*c, a*c)

        assert_array_almost_equal(a*csp, a*c)
        assert_array_almost_equal(a2*csp, a*c)
        csp = bsp.tocsr()
        assert_array_almost_equal((asp*csp).todense(), a*c)
        assert_array_almost_equal(asp*c, a*c)

        assert_array_almost_equal(a*csp, a*c)
        assert_array_almost_equal(a2*csp, a*c)
        csp = bsp.tocoo()
        assert_array_almost_equal((asp*csp).todense(), a*c)
        assert_array_almost_equal(asp*c, a*c)

        assert_array_almost_equal(a*csp, a*c)
        assert_array_almost_equal(a2*csp, a*c)

        # Test provided by Andy Fraser, 2006-03-26
        L = 30
        frac = .3
        random.seed(0)  # make runs repeatable
        A = zeros((L,2))
        for i in xrange(L):
            for j in xrange(2):
                r = random.random()
                if r < frac:
                    A[i,j] = r/frac

        A = self.spmatrix(A)
        B = A*A.T
        assert_array_almost_equal(B.todense(), A.todense() * A.T.todense())
        assert_array_almost_equal(B.todense(), A.todense() * A.todense().T)

        # check dimension mismatch  2x2 times 3x2
        A = self.spmatrix([[1,2],[3,4]])
        B = self.spmatrix([[1,2],[3,4],[5,6]])
        assert_raises(ValueError, A.__mul__, B)

    def test_matmat_dense(self):
        a = matrix([[3,0,0],[0,1,0],[2,0,3.0],[2,3,0]])
        asp = self.spmatrix(a)

        # check both array and matrix types
        bs = [array([[1,2],[3,4],[5,6]]), matrix([[1,2],[3,4],[5,6]])]

        for b in bs:
            result = asp*b
            assert_(isinstance(result, type(b)))
            assert_equal(result.shape, (4,2))
            assert_equal(result, dot(a,b))

    def test_sparse_format_conversions(self):
        A = sparse.kron([[1,0,2],[0,3,4],[5,0,0]], [[1,2],[0,3]])
        D = A.todense()
        A = self.spmatrix(A)

        for format in ['bsr','coo','csc','csr','dia','dok','lil']:
            a = A.asformat(format)
            assert_equal(a.format,format)
            assert_array_equal(a.todense(), D)

            b = self.spmatrix(D+3j).asformat(format)
            assert_equal(b.format,format)
            assert_array_equal(b.todense(), D+3j)

            c = eval(format + '_matrix')(A)
            assert_equal(c.format,format)
            assert_array_equal(c.todense(), D)

    def test_tobsr(self):
        x = array([[1,0,2,0],[0,0,0,0],[0,0,4,5]])
        y = array([[0,1,2],[3,0,5]])
        A = kron(x,y)
        Asp = self.spmatrix(A)
        for format in ['bsr']:
            fn = getattr(Asp, 'to' + format)

            for X in [1, 2, 3, 6]:
                for Y in [1, 2, 3, 4, 6, 12]:
                    assert_equal(fn(blocksize=(X,Y)).todense(), A)

    def test_transpose(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            a = datsp.transpose()
            b = dat.transpose()
            assert_array_equal(a.todense(), b)
            assert_array_equal(a.transpose().todense(), dat)

            assert_array_equal(self.spmatrix((3,4)).T.todense(), zeros((4,3)))

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_add_dense(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            # adding a dense matrix to a sparse matrix
            sum1 = dat + datsp
            assert_array_equal(sum1, dat + dat)
            sum2 = datsp + dat
            assert_array_equal(sum2, dat + dat)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_sub_dense(self):
        # subtracting a dense matrix to/from a sparse matrix
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            # Behavior is different for bool.
            if dat.dtype == bool:
                sum1 = dat - datsp
                assert_array_equal(sum1, dat - dat)
                sum2 = datsp - dat
                assert_array_equal(sum2, dat - dat)
            else:
                # Manually add to avoid upcasting from scalar
                # multiplication.
                sum1 = (dat + dat + dat) - datsp
                assert_array_equal(sum1, dat + dat)
                sum2 = (datsp + datsp + datsp) - dat
                assert_array_equal(sum2, dat + dat)

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_copy(self):
        # Check whether the copy=True and copy=False keywords work
        A = self.datsp

        # check that copy preserves format
        assert_equal(A.copy().format, A.format)
        assert_equal(A.__class__(A,copy=True).format, A.format)
        assert_equal(A.__class__(A,copy=False).format, A.format)

        assert_equal(A.copy().todense(), A.todense())
        assert_equal(A.__class__(A,copy=True).todense(), A.todense())
        assert_equal(A.__class__(A,copy=False).todense(), A.todense())

        # check that XXX_matrix.toXXX() works
        toself = getattr(A,'to' + A.format)
        assert_equal(toself().format, A.format)
        assert_equal(toself(copy=True).format, A.format)
        assert_equal(toself(copy=False).format, A.format)

        assert_equal(toself().todense(), A.todense())
        assert_equal(toself(copy=True).todense(), A.todense())
        assert_equal(toself(copy=False).todense(), A.todense())

        # check whether the data is copied?
        # TODO: deal with non-indexable types somehow
        B = A.copy()
        try:
            B[0,0] += 1
            assert_(B[0,0] != A[0,0])
        except NotImplementedError:
            # not all sparse matrices can be indexed
            pass
        except TypeError:
            # not all sparse matrices can be indexed
            pass

    # test that __iter__ is compatible with NumPy matrix
    def test_iterator(self):
        B = np.matrix(np.arange(50).reshape(5, 10))
        A = self.spmatrix(B)

        for x, y in zip(A, B):
            assert_equal(x.todense(), y)

    def test_size_zero_matrix_arithmetic(self):
        # Test basic matrix arithmatic with shapes like (0,0), (10,0),
        # (0, 3), etc.
        mat = np.matrix([])
        a = mat.reshape((0, 0))
        b = mat.reshape((0, 1))
        c = mat.reshape((0, 5))
        d = mat.reshape((1, 0))
        e = mat.reshape((5, 0))
        f = np.matrix(np.ones([5, 5]))

        asp = self.spmatrix(a)
        bsp = self.spmatrix(b)
        csp = self.spmatrix(c)
        dsp = self.spmatrix(d)
        esp = self.spmatrix(e)
        fsp = self.spmatrix(f)

        # matrix product.
        assert_array_equal(asp.dot(asp).A, np.dot(a, a).A)
        assert_array_equal(bsp.dot(dsp).A, np.dot(b, d).A)
        assert_array_equal(dsp.dot(bsp).A, np.dot(d, b).A)
        assert_array_equal(csp.dot(esp).A, np.dot(c, e).A)
        assert_array_equal(csp.dot(fsp).A, np.dot(c, f).A)
        assert_array_equal(esp.dot(csp).A, np.dot(e, c).A)
        assert_array_equal(dsp.dot(csp).A, np.dot(d, c).A)
        assert_array_equal(fsp.dot(esp).A, np.dot(f, e).A)

        # bad matrix products
        assert_raises(ValueError, dsp.dot, e)
        assert_raises(ValueError, asp.dot, d)

        # elemente-wise multiplication
        assert_array_equal(asp.multiply(asp).A, np.multiply(a, a).A)
        assert_array_equal(bsp.multiply(bsp).A, np.multiply(b, b).A)
        assert_array_equal(dsp.multiply(dsp).A, np.multiply(d, d).A)

        assert_array_equal(asp.multiply(a).A, np.multiply(a, a).A)
        assert_array_equal(bsp.multiply(b).A, np.multiply(b, b).A)
        assert_array_equal(dsp.multiply(d).A, np.multiply(d, d).A)

        assert_array_equal(asp.multiply(6).A, np.multiply(a, 6).A)
        assert_array_equal(bsp.multiply(6).A, np.multiply(b, 6).A)
        assert_array_equal(dsp.multiply(6).A, np.multiply(d, 6).A)

        # bad element-wise multiplication
        assert_raises(ValueError, asp.multiply, c)
        assert_raises(ValueError, esp.multiply, c)

        # Addition
        assert_array_equal(asp.__add__(asp).A, a.__add__(a).A)
        assert_array_equal(bsp.__add__(bsp).A, b.__add__(b).A)
        assert_array_equal(dsp.__add__(dsp).A, d.__add__(d).A)

        # bad addition
        assert_raises(ValueError, asp.__add__, dsp)
        assert_raises(ValueError, bsp.__add__, asp)

    def test_size_zero_conversions(self):
        mat = np.matrix([])
        a = mat.reshape((0, 0))
        b = mat.reshape((0, 5))
        c = mat.reshape((5, 0))

        for m in [a, b, c]:
            spm = self.spmatrix(m)
            assert_array_equal(spm.tocoo().A, m)
            assert_array_equal(spm.tocsr().A, m)
            assert_array_equal(spm.tocsc().A, m)
            assert_array_equal(spm.tolil().A, m)
            assert_array_equal(spm.todok().A, m)
            assert_array_equal(spm.tobsr().A, m)

    def test_unary_ufunc_overrides(self):
        def check(name):
            if LooseVersion(np.version.version) < LooseVersion('1.9'):
                if name == "sign":
                    raise nose.SkipTest("sign conflicts with comparison op "
                                        "support on Numpy < 1.9")
                if self.spmatrix in (dok_matrix, lil_matrix):
                    raise nose.SkipTest("Unary ops not implemented for dok/lil "
                                        "with Numpy < 1.9")
            ufunc = getattr(np, name)

            X = self.spmatrix(np.arange(20).reshape(4, 5) / 20.)
            X0 = ufunc(X.toarray())

            X2 = ufunc(X)
            assert_array_equal(X2.toarray(), X0)

            if not (LooseVersion(np.version.version) < LooseVersion('1.9')):
                # the out argument doesn't work on Numpy < 1.9
                out = np.zeros_like(X0)
                X3 = ufunc(X, out=out)
                assert_(X3 is out)
                assert_array_equal(todense(X3), ufunc(todense(X)))

                out = csc_matrix(out.shape, dtype=out.dtype)
                out[:,1] = 999
                X4 = ufunc(X, out=out)
                assert_(X4 is out)
                assert_array_equal(todense(X4), ufunc(todense(X)))

        for name in ["sin", "tan", "arcsin", "arctan", "sinh", "tanh",
                     "arcsinh", "arctanh", "rint", "sign", "expm1", "log1p",
                     "deg2rad", "rad2deg", "floor", "ceil", "trunc", "sqrt"]:
            yield check, name

    def test_binary_ufunc_overrides(self):
        # data
        a = np.array([[1, 2, 3],
                      [4, 5, 0],
                      [7, 8, 9]])
        b = np.array([[9, 8, 7],
                      [6, 0, 0],
                      [3, 2, 1]])
        c = 1.0
        d = 1 + 2j
        e = 5

        asp = self.spmatrix(a)
        bsp = self.spmatrix(b)

        a_items = dict(dense=a, scalar=c, cplx_scalar=d, int_scalar=e, sparse=asp)
        b_items = dict(dense=b, scalar=c, cplx_scalar=d, int_scalar=e, sparse=bsp)

        @dec.skipif(LooseVersion(np.version.version) < LooseVersion('1.9'),
                    "feature requires Numpy 1.9")
        def check(i, j, dtype):
            ax = a_items[i]
            bx = b_items[j]

            if isinstance(ax, self.spmatrix):
                ax = ax.astype(dtype)
            if isinstance(bx, self.spmatrix):
                bx = bx.astype(dtype)

            a = todense(ax)
            b = todense(bx)

            def check_one(ufunc, allclose=False):
                # without out argument
                expected = ufunc(a, b)
                got = ufunc(ax, bx)
                if allclose:
                    assert_allclose(todense(got), expected,
                                    rtol=5e-15, atol=0)
                else:
                    assert_array_equal(todense(got), expected)

                # with out argument
                out = np.zeros(got.shape, dtype=got.dtype)
                out.fill(np.nan)
                got = ufunc(ax, bx, out=out)
                assert_(got is out)
                if allclose:
                    assert_allclose(todense(got), expected,
                                    rtol=5e-15, atol=0)
                else:
                    assert_array_equal(todense(got), expected)

                out = csr_matrix(got.shape, dtype=out.dtype)
                out[0,:] = 999
                got = ufunc(ax, bx, out=out)
                assert_(got is out)
                if allclose:
                    assert_allclose(todense(got), expected,
                                    rtol=5e-15, atol=0)
                else:
                    assert_array_equal(todense(got), expected)

            # -- associative

            # multiply
            check_one(np.multiply)

            # add
            if isscalarlike(ax) or isscalarlike(bx):
                try:
                    check_one(np.add)
                except NotImplementedError:
                    # Not implemented for all spmatrix types
                    pass
            else:
                check_one(np.add)

            # -- non-associative

            # dot
            check_one(np.dot)

            # subtract
            if isscalarlike(ax) or isscalarlike(bx):
                try:
                    check_one(np.subtract)
                except NotImplementedError:
                    # Not implemented for all spmatrix types
                    pass
            else:
                check_one(np.subtract)

            # divide
            with np.errstate(divide='ignore', invalid='ignore'):
                if isscalarlike(bx):
                    # Rounding error may be different, as the sparse implementation
                    # computes a/b -> a * (1/b) if b is a scalar
                    check_one(np.divide, allclose=True)
                else:
                    check_one(np.divide)

                # true_divide
                if isscalarlike(bx):
                    check_one(np.true_divide, allclose=True)
                else:
                    check_one(np.true_divide)

        for i in a_items.keys():
            for j in b_items.keys():
                for dtype in [np.int_, np.float_, np.complex_]:
                    if i == 'sparse' or j == 'sparse':
                        yield check, i, j, dtype


class _TestInplaceArithmetic:
    @dec.skipif(LooseVersion(np.version.version) < LooseVersion('1.9'),
                "Not implemented with Numpy < 1.9")
    def test_inplace_dense_method(self):
        # Check that ndarray inplace ops work
        a = np.ones((3, 4))
        b = self.spmatrix(a)

        def check(op):
            x = a.copy()
            y = a.copy()

            x = getattr(x, op)(a)
            y = getattr(y, op)(b)

            assert_array_equal(x, y, err_msg=op)

        for op in ['__iadd__', '__isub__',
                   '__imul__', '__idiv__',
                   '__ifloordiv__', '__itruediv__']:
            c = dec.knownfailureif(
                op == '__ifloordiv__',
                "sparse floordiv not implemented")(check)
            yield c, op

    def test_inplace_dense_syntax(self):
        # Same as test_inplace_dense_method, but with the syntax
        a = np.ones((3, 4))
        b = self.spmatrix(a)

        x = a.copy()
        y = a.copy()
        x += a
        y += b
        assert_array_equal(x, y)

        x = a.copy()
        y = a.copy()
        x -= a
        y -= b
        assert_array_equal(x, y)

        if not (LooseVersion(np.version.version) < LooseVersion('1.9')):
            # These operations don't work properly without __numpy_ufunc__,
            # due to missing or incompatible __r*__ implementations

            # This is elementwise product
            x = a.copy()
            y = a.copy()
            x *= a
            y *= b
            assert_array_equal(x, y)

            x = a.copy()
            y = a.copy()
            x /= a
            y /= b
            assert_array_equal(x, y)

            # XXX: floor division is not implemented
            #x = a.copy()
            #y = a.copy()
            #x //= a
            #y //= b
            #assert_array_equal(x, y)

    def test_imul_scalar(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            # Avoid implicit casting.
            if _can_cast_samekind(type(2), dtype):
                a = datsp.copy()
                a *= 2
                b = dat.copy()
                b *= 2
                assert_array_equal(b, a.todense())

            if _can_cast_samekind(type(17.3), dtype):
                a = datsp.copy()
                a *= 17.3
                b = dat.copy()
                b *= 17.3
                assert_array_equal(b, a.todense())

        for dtype in self.checked_dtypes:
            yield check, dtype

    def test_idiv_scalar(self):
        def check(dtype):
            dat = self.dat_dtypes[dtype]
            datsp = self.datsp_dtypes[dtype]

            if _can_cast_samekind(type(2), dtype):
                a = datsp.copy()
                a /= 2
                b = dat.copy()
                b /= 2
                assert_array_equal(b, a.todense())

            if _can_cast_samekind(type(17.3), dtype):
                a = datsp.copy()
                a /= 17.3
                b = dat.copy()
                b /= 17.3
                assert_array_equal(b, a.todense())

        for dtype in self.checked_dtypes:
            # /= should only be used with float dtypes to avoid implicit
            # casting.
            if not np.can_cast(dtype, np.int_):
                yield check, dtype


class _TestGetSet:
    def test_getelement(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            D = array([[1,0,0],
                       [4,3,0],
                       [0,2,0],
                       [0,0,0]])
            A = self.spmatrix(D)

            M,N = D.shape

            for i in range(-M, M):
                for j in range(-N, N):
                    assert_equal(A[i,j], D[i,j])

            for ij in [(0,3),(-1,3),(4,0),(4,3),(4,-1), (1, 2, 3)]:
                assert_raises((IndexError, TypeError), A.__getitem__, ij)

    def test_setelement(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((3,4))
            A[0, 0] = 0  # bug 870
            A[1, 2] = 4.0
            A[0, 1] = 3
            A[2, 0] = 2.0
            A[0,-1] = 8
            A[-1,-2] = 7
            A[0, 1] = 5
            assert_array_equal(A.todense(),[[0,5,0,8],[0,0,4,0],[2,0,7,0]])

            for ij in [(0,4),(-1,4),(3,0),(3,4),(3,-1)]:
                assert_raises(IndexError, A.__setitem__, ij, 123.0)

            for v in [[1,2,3], array([1,2,3])]:
                assert_raises(ValueError, A.__setitem__, (0,0), v)

            for v in [3j]:
                assert_raises(TypeError, A.__setitem__, (0,0), v)

    def test_scalar_assign_2(self):
        n, m = (5, 10)

        def _test_set(i, j, nitems):
            msg = "%r ; %r ; %r" % (i, j, nitems)
            A = self.spmatrix((n, m))
            A[i, j] = 1
            assert_almost_equal(A.sum(), nitems, err_msg=msg)
            assert_almost_equal(A[i, j], 1, err_msg=msg)

        # [i,j]
        for i, j in [(2, 3), (-1, 8), (-1, -2), (array(-1), -2), (-1, array(-2)),
                     (array(-1), array(-2))]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                _test_set(i, j, 1)

    def test_index_scalar_assign(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((5, 5))
            B = np.zeros((5, 5))
            for C in [A, B]:
                C[0,1] = 1
                C[3,0] = 4
                C[3,0] = 9
            assert_array_equal(A.toarray(), B)


class _TestSolve:
    def test_solve(self):
        # Test whether the lu_solve command segfaults, as reported by Nils
        # Wagner for a 64-bit machine, 02 March 2005 (EJS)
        n = 20
        np.random.seed(0)  # make tests repeatable
        A = zeros((n,n), dtype=complex)
        x = np.random.rand(n)
        y = np.random.rand(n-1)+1j*np.random.rand(n-1)
        r = np.random.rand(n)
        for i in range(len(x)):
            A[i,i] = x[i]
        for i in range(len(y)):
            A[i,i+1] = y[i]
            A[i+1,i] = conjugate(y[i])
        A = self.spmatrix(A)
        x = splu(A).solve(r)
        assert_almost_equal(A*x,r)


class _TestSlicing:
    def test_dtype_preservation(self):
        assert_equal(self.spmatrix((1,10), dtype=np.int16)[0,1:5].dtype, np.int16)
        assert_equal(self.spmatrix((1,10), dtype=np.int32)[0,1:5].dtype, np.int32)
        assert_equal(self.spmatrix((1,10), dtype=np.float32)[0,1:5].dtype, np.float32)
        assert_equal(self.spmatrix((1,10), dtype=np.float64)[0,1:5].dtype, np.float64)
    def test_get_horiz_slice(self):
        B = asmatrix(arange(50.).reshape(5,10))
        A = self.spmatrix(B)
        assert_array_equal(B[1,:], A[1,:].todense())
        assert_array_equal(B[1,2:5], A[1,2:5].todense())

        C = matrix([[1, 2, 1], [4, 0, 6], [0, 0, 0], [0, 0, 1]])
        D = self.spmatrix(C)
        assert_array_equal(C[1, 1:3], D[1, 1:3].todense())

        # Now test slicing when a row contains only zeros
        E = matrix([[1, 2, 1], [4, 0, 0], [0, 0, 0], [0, 0, 1]])
        F = self.spmatrix(E)
        assert_array_equal(E[1, 1:3], F[1, 1:3].todense())
        assert_array_equal(E[2, -2:], F[2, -2:].A)

        # The following should raise exceptions:
        assert_raises(IndexError, A.__getitem__, (slice(None), 11))
        assert_raises(IndexError, A.__getitem__, (6, slice(3, 7)))

    def test_get_vert_slice(self):
        B = asmatrix(arange(50.).reshape(5,10))
        A = self.spmatrix(B)
        assert_array_equal(B[2:5,0], A[2:5,0].todense())
        assert_array_equal(B[:,1], A[:,1].todense())

        C = matrix([[1, 2, 1], [4, 0, 6], [0, 0, 0], [0, 0, 1]])
        D = self.spmatrix(C)
        assert_array_equal(C[1:3, 1], D[1:3, 1].todense())
        assert_array_equal(C[:, 2], D[:, 2].todense())

        # Now test slicing when a column contains only zeros
        E = matrix([[1, 0, 1], [4, 0, 0], [0, 0, 0], [0, 0, 1]])
        F = self.spmatrix(E)
        assert_array_equal(E[:, 1], F[:, 1].todense())
        assert_array_equal(E[-2:, 2], F[-2:, 2].todense())

        # The following should raise exceptions:
        assert_raises(IndexError, A.__getitem__, (slice(None), 11))
        assert_raises(IndexError, A.__getitem__, (6, slice(3, 7)))

    def test_get_slices(self):
        B = asmatrix(arange(50.).reshape(5,10))
        A = self.spmatrix(B)
        assert_array_equal(A[2:5,0:3].todense(), B[2:5,0:3])
        assert_array_equal(A[1:,:-1].todense(), B[1:,:-1])
        assert_array_equal(A[:-1,1:].todense(), B[:-1,1:])

        # Now test slicing when a column contains only zeros
        E = matrix([[1, 0, 1], [4, 0, 0], [0, 0, 0], [0, 0, 1]])
        F = self.spmatrix(E)
        assert_array_equal(E[1:2, 1:2], F[1:2, 1:2].todense())
        assert_array_equal(E[:, 1:], F[:, 1:].todense())

    def test_non_unit_stride_2d_indexing(self):
        # Regression test -- used to silently ignore the stride.
        v0 = np.random.rand(50, 50)
        try:
            v = self.spmatrix(v0)[0:25:2, 2:30:3]
        except ValueError:
            # if unsupported
            raise nose.SkipTest("feature not implemented")

        assert_array_equal(v.todense(),
                           v0[0:25:2, 2:30:3])

    def test_slicing_2(self):
        B = asmatrix(arange(50).reshape(5,10))
        A = self.spmatrix(B)

        # [i,j]
        assert_equal(A[2,3], B[2,3])
        assert_equal(A[-1,8], B[-1,8])
        assert_equal(A[-1,-2],B[-1,-2])
        assert_equal(A[array(-1),-2],B[-1,-2])
        assert_equal(A[-1,array(-2)],B[-1,-2])
        assert_equal(A[array(-1),array(-2)],B[-1,-2])

        # [i,1:2]
        assert_equal(A[2,:].todense(), B[2,:])
        assert_equal(A[2,5:-2].todense(),B[2,5:-2])
        assert_equal(A[array(2),5:-2].todense(),B[2,5:-2])

        # [1:2,j]
        assert_equal(A[:,2].todense(), B[:,2])
        assert_equal(A[3:4,9].todense(), B[3:4,9])
        assert_equal(A[1:4,-5].todense(),B[1:4,-5])
        assert_equal(A[2:-1,3].todense(),B[2:-1,3])
        assert_equal(A[2:-1,array(3)].todense(),B[2:-1,3])

        # [1:2,1:2]
        assert_equal(A[1:2,1:2].todense(),B[1:2,1:2])
        assert_equal(A[4:,3:].todense(), B[4:,3:])
        assert_equal(A[:4,:5].todense(), B[:4,:5])
        assert_equal(A[2:-1,:5].todense(),B[2:-1,:5])

        # [i]
        assert_equal(A[1,:].todense(), B[1,:])
        assert_equal(A[-2,:].todense(),B[-2,:])
        assert_equal(A[array(-2),:].todense(),B[-2,:])

        # [1:2]
        assert_equal(A[1:4].todense(), B[1:4])
        assert_equal(A[1:-2].todense(),B[1:-2])

        # Check bug reported by Robert Cimrman:
        # http://thread.gmane.org/gmane.comp.python.scientific.devel/7986
        s = slice(int8(2),int8(4),None)
        assert_equal(A[s,:].todense(), B[2:4,:])
        assert_equal(A[:,s].todense(), B[:,2:4])

    def test_slicing_3(self):
        B = asmatrix(arange(50).reshape(5,10))
        A = self.spmatrix(B)

        s_ = np.s_
        slices = [s_[:2], s_[1:2], s_[3:], s_[3::2],
                  s_[8:3:-1], s_[4::-2], s_[:5:-1],
                  0, 1, s_[:], s_[1:5], -1, -2, -5,
                  array(-1), np.int8(-3)]

        def check_1(a):
            x = A[a]
            y = B[a]
            if y.shape == ():
                assert_equal(x, y, repr(a))
            else:
                if x.size == 0 and y.size == 0:
                    pass
                else:
                    assert_array_equal(x.todense(), y, repr(a))

        for j, a in enumerate(slices):
            yield check_1, a

        def check_2(a, b):
            # Indexing np.matrix with 0-d arrays seems to be broken,
            # as they seem not to be treated as scalars.
            # https://github.com/numpy/numpy/issues/3110
            if isinstance(a, np.ndarray):
                ai = int(a)
            else:
                ai = a
            if isinstance(b, np.ndarray):
                bi = int(b)
            else:
                bi = b

            x = A[a, b]
            y = B[ai, bi]

            if y.shape == ():
                assert_equal(x, y, repr((a, b)))
            else:
                if x.size == 0 and y.size == 0:
                    pass
                else:
                    assert_array_equal(x.todense(), y, repr((a, b)))

        for i, a in enumerate(slices):
            for j, b in enumerate(slices):
                yield check_2, a, b

    def test_ellipsis_slicing(self):
        b = asmatrix(arange(50).reshape(5,10))
        a = self.spmatrix(b)

        assert_array_equal(a[...].A, b[...].A)
        assert_array_equal(a[...,].A, b[...,].A)

        assert_array_equal(a[..., ...].A, b[..., ...].A)
        assert_array_equal(a[1, ...].A, b[1, ...].A)
        assert_array_equal(a[..., 1].A, b[..., 1].A)
        assert_array_equal(a[1:, ...].A, b[1:, ...].A)
        assert_array_equal(a[..., 1:].A, b[..., 1:].A)

        assert_array_equal(a[..., ..., ...].A, b[..., ..., ...].A)
        assert_array_equal(a[1, ..., ...].A, b[1, ..., ...].A)
        assert_array_equal(a[1:, ..., ...].A, b[1:, ..., ...].A)
        assert_array_equal(a[..., ..., 1:].A, b[..., ..., 1:].A)
        assert_array_equal(a[1:, 1, ...].A, b[1:, 1, ...].A)
        assert_array_equal(a[1, ..., 1:].A, b[1, ..., 1:].A)
        # These return ints
        assert_equal(a[1, 1, ...], b[1, 1, ...])
        assert_equal(a[1, ..., 1], b[1, ..., 1])
        # Bug in NumPy's slicing
        assert_array_equal(a[..., ..., 1].A, b[..., ..., 1].A.reshape((5,1)))


class _TestSlicingAssign:
    def test_slice_scalar_assign(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((5, 5))
            B = np.zeros((5, 5))
            for C in [A, B]:
                C[0:1,1] = 1
                C[3:0,0] = 4
                C[3:4,0] = 9
                C[0,4:] = 1
                C[3::-1,4:] = 9
            assert_array_equal(A.toarray(), B)

    def test_slice_assign_2(self):
        n, m = (5, 10)

        def _test_set(i, j):
            msg = "i=%r; j=%r" % (i, j)
            A = self.spmatrix((n, m))
            A[i, j] = 1
            B = np.zeros((n, m))
            B[i, j] = 1
            assert_array_almost_equal(A.todense(), B, err_msg=msg)
        # [i,1:2]
        for i, j in [(2, slice(3)), (2, slice(None, 10, 4)), (2, slice(5, -2)),
                     (array(2), slice(5, -2))]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
                _test_set(i, j)

    def test_self_self_assignment(self):
        # Tests whether a row of one lil_matrix can be assigned to
        # another.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            B = self.spmatrix((4,3))
            B[0,0] = 2
            B[1,2] = 7
            B[2,1] = 3
            B[3,0] = 10

            A = B / 10
            B[0,:] = A[0,:]
            assert_array_equal(A[0,:].A, B[0,:].A)

            A = B / 10
            B[:,:] = A[:1,:1]
            assert_equal(A[0,0], B[3,2])

            A = B / 10
            B[:-1,0] = A[0,:].T
            assert_array_equal(A[0,:].A.T, B[:-1,0].A)

    def test_slice_assignment(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            B = self.spmatrix((4,3))
            B[0,0] = 5
            B[1,2] = 3
            B[2,1] = 7

            expected = array([[10,0,0],
                              [0,0,6],
                              [0,14,0],
                              [0,0,0]])

            B[:,:] = B+B
            assert_array_equal(B.todense(),expected)

            block = [[1,0],[0,4]]
            B[:2,:2] = csc_matrix(array(block))
            assert_array_equal(B.todense()[:2,:2],block)

    def test_set_slice(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((5,10))
            B = matrix(zeros((5,10), float))

            s_ = np.s_
            slices = [s_[:2], s_[1:2], s_[3:], s_[3::2],
                      s_[8:3:-1], s_[4::-2], s_[:5:-1],
                      0, 1, s_[:], s_[1:5], -1, -2, -5,
                      array(-1), np.int8(-3)]

            for j, a in enumerate(slices):
                A[a] = j
                B[a] = j
                assert_array_equal(A.todense(), B, repr(a))

            for i, a in enumerate(slices):
                for j, b in enumerate(slices):
                    A[a,b] = 10*i + 1000*(j+1)
                    B[a,b] = 10*i + 1000*(j+1)
                    assert_array_equal(A.todense(), B, repr((a, b)))

            A[0, 1:10:2] = xrange(1,10,2)
            B[0, 1:10:2] = xrange(1,10,2)
            assert_array_equal(A.todense(), B)
            A[1:5:2,0] = np.array(range(1,5,2))[:,None]
            B[1:5:2,0] = np.array(range(1,5,2))[:,None]
            assert_array_equal(A.todense(), B)

            # The next commands should raise exceptions
            assert_raises(ValueError, A.__setitem__, (0, 0), list(range(100)))
            assert_raises(ValueError, A.__setitem__, (0, 0), arange(100))
            assert_raises(ValueError, A.__setitem__, (0, slice(None)),
                          list(range(100)))
            assert_raises(ValueError, A.__setitem__, (slice(None), 1),
                          list(range(100)))
            assert_raises(ValueError, A.__setitem__, (slice(None), 1), A.copy())
            assert_raises(ValueError, A.__setitem__,
                          ([[1, 2, 3], [0, 3, 4]], [1, 2, 3]), [1, 2, 3, 4])
            assert_raises(ValueError, A.__setitem__,
                          ([[1, 2, 3], [0, 3, 4], [4, 1, 3]],
                           [[1, 2, 4], [0, 1, 3]]), [2, 3, 4])


class _TestFancyIndexing:
    """Tests fancy indexing features.  The tests for any matrix formats
    that implement these features should derive from this class.
    """

    def test_bad_index(self):
        A = self.spmatrix(np.zeros([5, 5]))
        assert_raises((IndexError, ValueError, TypeError), A.__getitem__, "foo")
        assert_raises((IndexError, ValueError, TypeError), A.__getitem__, (2, "foo"))
        assert_raises((IndexError, ValueError), A.__getitem__,
                      ([1, 2, 3], [1, 2, 3, 4]))

    def test_fancy_indexing(self):
        B = asmatrix(arange(50).reshape(5,10))
        A = self.spmatrix(B)

        # [i]
        assert_equal(A[[1,3]].todense(), B[[1,3]])

        # [i,[1,2]]
        assert_equal(A[3,[1,3]].todense(), B[3,[1,3]])
        assert_equal(A[-1,[2,-5]].todense(),B[-1,[2,-5]])
        assert_equal(A[array(-1),[2,-5]].todense(),B[-1,[2,-5]])
        assert_equal(A[-1,array([2,-5])].todense(),B[-1,[2,-5]])
        assert_equal(A[array(-1),array([2,-5])].todense(),B[-1,[2,-5]])

        # [1:2,[1,2]]
        assert_equal(A[:,[2,8,3,-1]].todense(),B[:,[2,8,3,-1]])
        assert_equal(A[3:4,[9]].todense(), B[3:4,[9]])
        assert_equal(A[1:4,[-1,-5]].todense(), B[1:4,[-1,-5]])
        assert_equal(A[1:4,array([-1,-5])].todense(), B[1:4,[-1,-5]])

        # [[1,2],j]
        assert_equal(A[[1,3],3].todense(), B[[1,3],3])
        assert_equal(A[[2,-5],-4].todense(), B[[2,-5],-4])
        assert_equal(A[array([2,-5]),-4].todense(), B[[2,-5],-4])
        assert_equal(A[[2,-5],array(-4)].todense(), B[[2,-5],-4])
        assert_equal(A[array([2,-5]),array(-4)].todense(), B[[2,-5],-4])

        # [[1,2],1:2]
        assert_equal(A[[1,3],:].todense(), B[[1,3],:])
        assert_equal(A[[2,-5],8:-1].todense(),B[[2,-5],8:-1])
        assert_equal(A[array([2,-5]),8:-1].todense(),B[[2,-5],8:-1])

        # [[1,2],[1,2]]
        assert_equal(todense(A[[1,3],[2,4]]), B[[1,3],[2,4]])
        assert_equal(todense(A[[-1,-3],[2,-4]]), B[[-1,-3],[2,-4]])
        assert_equal(todense(A[array([-1,-3]),[2,-4]]), B[[-1,-3],[2,-4]])
        assert_equal(todense(A[[-1,-3],array([2,-4])]), B[[-1,-3],[2,-4]])
        assert_equal(todense(A[array([-1,-3]),array([2,-4])]), B[[-1,-3],[2,-4]])

        # [[[1],[2]],[1,2]]
        assert_equal(A[[[1],[3]],[2,4]].todense(), B[[[1],[3]],[2,4]])
        assert_equal(A[[[-1],[-3],[-2]],[2,-4]].todense(),B[[[-1],[-3],[-2]],[2,-4]])
        assert_equal(A[array([[-1],[-3],[-2]]),[2,-4]].todense(),B[[[-1],[-3],[-2]],[2,-4]])
        assert_equal(A[[[-1],[-3],[-2]],array([2,-4])].todense(),B[[[-1],[-3],[-2]],[2,-4]])
        assert_equal(A[array([[-1],[-3],[-2]]),array([2,-4])].todense(),B[[[-1],[-3],[-2]],[2,-4]])

        # [[1,2]]
        assert_equal(A[[1,3]].todense(), B[[1,3]])
        assert_equal(A[[-1,-3]].todense(),B[[-1,-3]])
        assert_equal(A[array([-1,-3])].todense(),B[[-1,-3]])

        # [[1,2],:][:,[1,2]]
        assert_equal(A[[1,3],:][:,[2,4]].todense(), B[[1,3],:][:,[2,4]])
        assert_equal(A[[-1,-3],:][:,[2,-4]].todense(), B[[-1,-3],:][:,[2,-4]])
        assert_equal(A[array([-1,-3]),:][:,array([2,-4])].todense(), B[[-1,-3],:][:,[2,-4]])

        # [:,[1,2]][[1,2],:]
        assert_equal(A[:,[1,3]][[2,4],:].todense(), B[:,[1,3]][[2,4],:])
        assert_equal(A[:,[-1,-3]][[2,-4],:].todense(), B[:,[-1,-3]][[2,-4],:])
        assert_equal(A[:,array([-1,-3])][array([2,-4]),:].todense(), B[:,[-1,-3]][[2,-4],:])

        # Check bug reported by Robert Cimrman:
        # http://thread.gmane.org/gmane.comp.python.scientific.devel/7986
        s = slice(int8(2),int8(4),None)
        assert_equal(A[s,:].todense(), B[2:4,:])
        assert_equal(A[:,s].todense(), B[:,2:4])

    def test_fancy_indexing_randomized(self):
        random.seed(1234)  # make runs repeatable

        NUM_SAMPLES = 50
        M = 6
        N = 4

        D = np.asmatrix(np.random.rand(M,N))
        D = np.multiply(D, D > 0.5)

        I = np.random.random_integers(-M + 1, M - 1, size=NUM_SAMPLES)
        J = np.random.random_integers(-N + 1, N - 1, size=NUM_SAMPLES)

        S = self.spmatrix(D)

        SIJ = S[I,J]
        if isspmatrix(SIJ):
            SIJ = SIJ.todense()
        assert_equal(SIJ, D[I,J])

        I_bad = I + M
        J_bad = J - N

        assert_raises(IndexError, S.__getitem__, (I_bad,J))
        assert_raises(IndexError, S.__getitem__, (I,J_bad))

    def test_fancy_indexing_boolean(self):
        random.seed(1234)  # make runs repeatable

        B = asmatrix(arange(50).reshape(5,10))
        A = self.spmatrix(B)

        I = np.array(np.random.randint(0, 2, size=5), dtype=bool)
        J = np.array(np.random.randint(0, 2, size=10), dtype=bool)
        X = np.array(np.random.randint(0, 2, size=(5, 10)), dtype=bool)

        assert_equal(todense(A[I]), B[I])
        assert_equal(todense(A[:,J]), B[:, J])
        assert_equal(todense(A[X]), B[X])
        assert_equal(todense(A[B > 9]), B[B > 9])

        I = np.array([True, False, True, True, False])
        J = np.array([False, True, True, False, True])

        assert_equal(todense(A[I, J]), B[I, J])

        Z = np.array(np.random.randint(0, 2, size=(5, 11)), dtype=bool)
        Y = np.array(np.random.randint(0, 2, size=(6, 10)), dtype=bool)

        assert_raises(IndexError, A.__getitem__, Z)
        assert_raises(IndexError, A.__getitem__, Y)
        assert_raises((IndexError, ValueError), A.__getitem__, (X, 1))

    def test_fancy_indexing_sparse_boolean(self):
        random.seed(1234)  # make runs repeatable

        B = asmatrix(arange(50).reshape(5,10))
        A = self.spmatrix(B)

        X = np.array(np.random.randint(0, 2, size=(5, 10)), dtype=bool)

        Xsp = csr_matrix(X)

        assert_equal(todense(A[Xsp]), B[X])
        assert_equal(todense(A[A > 9]), B[B > 9])

        Z = np.array(np.random.randint(0, 2, size=(5, 11)), dtype=bool)
        Y = np.array(np.random.randint(0, 2, size=(6, 10)), dtype=bool)

        Zsp = csr_matrix(Z)
        Ysp = csr_matrix(Y)

        assert_raises(IndexError, A.__getitem__, Zsp)
        assert_raises(IndexError, A.__getitem__, Ysp)
        assert_raises((IndexError, ValueError), A.__getitem__, (Xsp, 1))


class _TestFancyIndexingAssign:
    def test_bad_index_assign(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix(np.zeros([5, 5]))
            assert_raises((IndexError, ValueError, TypeError), A.__setitem__, "foo", 2)
            assert_raises((IndexError, ValueError, TypeError), A.__setitem__, (2, "foo"), 5)

    def test_fancy_indexing_set(self):
        n, m = (5, 10)

        def _test_set_slice(i, j):
            A = self.spmatrix((n, m))
            A[i, j] = 1
            B = asmatrix(np.zeros((n, m)))
            B[i, j] = 1
            assert_array_almost_equal(A.todense(), B)
        # [1:2,1:2]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            for i, j in [((2, 3, 4), slice(None, 10, 4)),
                         (np.arange(3), slice(5, -2)),
                         (slice(2, 5), slice(5, -2))]:
                _test_set_slice(i, j)
            for i, j in [(np.arange(3), np.arange(3)), ((0, 3, 4), (1, 2, 4))]:
                _test_set_slice(i, j)

    def test_sequence_assignment(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((4,3))
            B = self.spmatrix(eye(3,4))

            i0 = [0,1,2]
            i1 = (0,1,2)
            i2 = array(i0)

            A[0,i0] = B[i0,0].T
            A[1,i1] = B[i1,1].T
            A[2,i2] = B[i2,2].T
            assert_array_equal(A.todense(),B.T.todense())

            # column slice
            A = self.spmatrix((2,3))
            A[1,1:3] = [10,20]
            assert_array_equal(A.todense(), [[0,0,0],[0,10,20]])

            # row slice
            A = self.spmatrix((3,2))
            A[1:3,1] = [[10],[20]]
            assert_array_equal(A.todense(), [[0,0],[0,10],[0,20]])

            # both slices
            A = self.spmatrix((3,3))
            B = asmatrix(np.zeros((3,3)))
            for C in [A, B]:
                C[[0,1,2], [0,1,2]] = [4,5,6]
            assert_array_equal(A.toarray(), B)

            # both slices (2)
            A = self.spmatrix((4, 3))
            A[(1, 2, 3), (0, 1, 2)] = [1, 2, 3]
            assert_almost_equal(A.sum(), 6)
            B = asmatrix(np.zeros((4, 3)))
            B[(1, 2, 3), (0, 1, 2)] = [1, 2, 3]
            assert_array_equal(A.todense(), B)


class _TestFancyMultidim:
    def test_fancy_indexing_ndarray(self):
        sets = [
            (np.array([[1], [2], [3]]), np.array([3, 4, 2])),
            (np.array([[1], [2], [3]]), np.array([[3, 4, 2]])),
            (np.array([[1, 2, 3]]), np.array([[3], [4], [2]])),
            (np.array([1, 2, 3]), np.array([[3], [4], [2]])),
            (np.array([[1, 2, 3], [3, 4, 2]]),
             np.array([[5, 6, 3], [2, 3, 1]]))
            ]
        # These inputs generate 3-D outputs
        #    (np.array([[[1], [2], [3]], [[3], [4], [2]]]),
        #     np.array([[[5], [6], [3]], [[2], [3], [1]]])),

        for I, J in sets:
            np.random.seed(1234)
            D = np.asmatrix(np.random.rand(5, 7))
            S = self.spmatrix(D)

            SIJ = S[I,J]
            if isspmatrix(SIJ):
                SIJ = SIJ.todense()
            assert_equal(SIJ, D[I,J])

            I_bad = I + 5
            J_bad = J + 7

            assert_raises(IndexError, S.__getitem__, (I_bad,J))
            assert_raises(IndexError, S.__getitem__, (I,J_bad))

            # This would generate 3-D arrays -- not supported
            assert_raises(IndexError, S.__getitem__, ([I, I], slice(None)))
            assert_raises(IndexError, S.__getitem__, (slice(None), [J, J]))


class _TestFancyMultidimAssign:
    def test_fancy_assign_ndarray(self):
        np.random.seed(1234)

        D = np.asmatrix(np.random.rand(5, 7))
        S = self.spmatrix(D)
        X = np.random.rand(2, 3)

        I = np.array([[1, 2, 3], [3, 4, 2]])
        J = np.array([[5, 6, 3], [2, 3, 1]])

        S[I,J] = X
        D[I,J] = X
        assert_equal(S.todense(), D)

        I_bad = I + 5
        J_bad = J + 7

        C = [1, 2, 3]

        S[I,J] = C
        D[I,J] = C
        assert_equal(S.todense(), D)

        S[I,J] = 3
        D[I,J] = 3
        assert_equal(S.todense(), D)

        assert_raises(IndexError, S.__setitem__, (I_bad,J), C)
        assert_raises(IndexError, S.__setitem__, (I,J_bad), C)

    def test_fancy_indexing_multidim_set(self):
        n, m = (5, 10)

        def _test_set_slice(i, j):
            A = self.spmatrix((n, m))
            A[i, j] = 1
            B = asmatrix(np.zeros((n, m)))
            B[i, j] = 1
            assert_array_almost_equal(A.todense(), B)
        # [[[1, 2], [1, 2]], [1, 2]]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            for i, j in [(np.array([[1, 2], [1, 3]]), [1, 3]),
                            (np.array([0, 4]), [[0, 3], [1, 2]]),
                            ([[1, 2, 3], [0, 2, 4]], [[0, 4, 3], [4, 1, 2]])]:
                _test_set_slice(i, j)

    def test_fancy_assign_list(self):
        np.random.seed(1234)

        D = np.asmatrix(np.random.rand(5, 7))
        S = self.spmatrix(D)
        X = np.random.rand(2, 3)

        I = [[1, 2, 3], [3, 4, 2]]
        J = [[5, 6, 3], [2, 3, 1]]

        S[I,J] = X
        D[I,J] = X
        assert_equal(S.todense(), D)

        I_bad = [[ii + 5 for ii in i] for i in I]
        J_bad = [[jj + 7 for jj in j] for j in J]
        C = [1, 2, 3]

        S[I,J] = C
        D[I,J] = C
        assert_equal(S.todense(), D)

        S[I,J] = 3
        D[I,J] = 3
        assert_equal(S.todense(), D)

        assert_raises(IndexError, S.__setitem__, (I_bad,J), C)
        assert_raises(IndexError, S.__setitem__, (I,J_bad), C)

    def test_fancy_assign_slice(self):
        np.random.seed(1234)

        D = np.asmatrix(np.random.rand(5, 7))
        S = self.spmatrix(D)
        X = np.random.rand(2, 3)

        I = [[1, 2, 3], [3, 4, 2]]
        J = [[5, 6, 3], [2, 3, 1]]

        I_bad = [[ii + 5 for ii in i] for i in I]
        J_bad = [[jj + 7 for jj in j] for j in J]

        C = [1, 2, 3, 4, 5, 6, 7]
        assert_raises(IndexError, S.__setitem__, (I_bad, slice(None)), C)
        assert_raises(IndexError, S.__setitem__, (slice(None), J_bad), C)


class _TestArithmetic:
    """
    Test real/complex arithmetic
    """
    def __arith_init(self):
        # these can be represented exactly in FP (so arithmetic should be exact)
        self.__A = matrix([[-1.5, 6.5, 0, 2.25, 0, 0],
                         [3.125, -7.875, 0.625, 0, 0, 0],
                         [0, 0, -0.125, 1.0, 0, 0],
                         [0, 0, 8.375, 0, 0, 0]],'float64')
        self.__B = matrix([[0.375, 0, 0, 0, -5, 2.5],
                         [14.25, -3.75, 0, 0, -0.125, 0],
                         [0, 7.25, 0, 0, 0, 0],
                         [18.5, -0.0625, 0, 0, 0, 0]],'complex128')
        self.__B.imag = matrix([[1.25, 0, 0, 0, 6, -3.875],
                              [2.25, 4.125, 0, 0, 0, 2.75],
                              [0, 4.125, 0, 0, 0, 0],
                              [-0.0625, 0, 0, 0, 0, 0]],'float64')

        # fractions are all x/16ths
        assert_array_equal((self.__A*16).astype('int32'),16*self.__A)
        assert_array_equal((self.__B.real*16).astype('int32'),16*self.__B.real)
        assert_array_equal((self.__B.imag*16).astype('int32'),16*self.__B.imag)

        self.__Asp = self.spmatrix(self.__A)
        self.__Bsp = self.spmatrix(self.__B)

    def test_add_sub(self):
        self.__arith_init()

        # basic tests
        assert_array_equal((self.__Asp+self.__Bsp).todense(),self.__A+self.__B)

        # check conversions
        for x in supported_dtypes:
            A = self.__A.astype(x)
            Asp = self.spmatrix(A)
            for y in supported_dtypes:
                if not np.issubdtype(y, np.complexfloating):
                    B = self.__B.real.astype(y)
                else:
                    B = self.__B.astype(y)
                Bsp = self.spmatrix(B)

                # addition
                D1 = A + B
                S1 = Asp + Bsp

                assert_equal(S1.dtype,D1.dtype)
                assert_array_equal(S1.todense(),D1)
                assert_array_equal(Asp + B,D1)          # check sparse + dense
                assert_array_equal(A + Bsp,D1)          # check dense + sparse

                # subtraction
                D1 = A - B
                S1 = Asp - Bsp

                assert_equal(S1.dtype,D1.dtype)
                assert_array_equal(S1.todense(),D1)
                assert_array_equal(Asp - B,D1)          # check sparse - dense
                assert_array_equal(A - Bsp,D1)          # check dense - sparse

    def test_mu(self):
        self.__arith_init()

        # basic tests
        assert_array_equal((self.__Asp*self.__Bsp.T).todense(),self.__A*self.__B.T)

        for x in supported_dtypes:
            A = self.__A.astype(x)
            Asp = self.spmatrix(A)
            for y in supported_dtypes:
                if np.issubdtype(y, np.complexfloating):
                    B = self.__B.astype(y)
                else:
                    B = self.__B.real.astype(y)
                Bsp = self.spmatrix(B)

                D1 = A * B.T
                S1 = Asp * Bsp.T

                assert_array_equal(S1.todense(),D1)
                assert_equal(S1.dtype,D1.dtype)


class _TestMinMax(object):
    def test_minmax(self):
        for dtype in [np.float32, np.float64, np.int32, np.int64]:
            D = np.arange(20, dtype=dtype).reshape(5,4)

            X = self.spmatrix(D)
            assert_equal(X.min(), 0)
            assert_equal(X.max(), 19)
            assert_equal(X.min().dtype, dtype)
            assert_equal(X.max().dtype, dtype)

            D *= -1
            X = self.spmatrix(D)
            assert_equal(X.min(), -19)
            assert_equal(X.max(), 0)

            D += 5
            X = self.spmatrix(D)
            assert_equal(X.min(), -14)
            assert_equal(X.max(), 5)

        # try a fully dense matrix
        X = self.spmatrix(np.arange(1, 10).reshape(3, 3))
        assert_equal(X.min(), 1)
        assert_equal(X.min().dtype, X.dtype)

        X = -X
        assert_equal(X.max(), -1)

        # and a fully sparse matrix
        Z = self.spmatrix(np.zeros(1))
        assert_equal(Z.min(), 0)
        assert_equal(Z.max(), 0)
        assert_equal(Z.max().dtype, Z.dtype)

        # another test
        D = np.arange(20, dtype=float).reshape(5,4)
        D[0:2, :] = 0
        X = self.spmatrix(D)
        assert_equal(X.min(), 0)
        assert_equal(X.max(), 19)

    def test_minmax_axis(self):
        def check():
            D = np.matrix(np.arange(50).reshape(5,10))
            X = self.spmatrix(D)
            assert_array_equal(X.max(axis=0).A, D.max(axis=0).A)
            assert_array_equal(X.max(axis=1).A, D.max(axis=1).A)

            assert_array_equal(X.min(axis=0).A, D.min(axis=0).A)
            assert_array_equal(X.min(axis=1).A, D.min(axis=1).A)

        yield check


#------------------------------------------------------------------------------
# Tailored base class for generic tests
#------------------------------------------------------------------------------

def _possibly_unimplemented(cls, require=True):
    """
    Construct a class that either runs tests as usual (require=True),
    or each method raises SkipTest if it encounters a common error.
    """
    if require:
        return cls
    else:
        def wrap(fc):
            def wrapper(*a, **kw):
                try:
                    return fc(*a, **kw)
                except (NotImplementedError, TypeError, ValueError,
                        IndexError, AttributeError):
                    raise nose.SkipTest("feature not implemented")

            wrapper.__name__ = fc.__name__
            return wrapper

        new_dict = dict(cls.__dict__)
        for name, func in cls.__dict__.items():
            if name.startswith('test_'):
                new_dict[name] = wrap(func)
        return type(cls.__name__ + "NotImplemented",
                    cls.__bases__,
                    new_dict)


def sparse_test_class(getset=True, slicing=True, slicing_assign=True,
                      fancy_indexing=True, fancy_assign=True,
                      fancy_multidim_indexing=True, fancy_multidim_assign=True,
                      minmax=True):
    """
    Construct a base class, optionally converting some of the tests in
    the suite to check that the feature is not implemented.
    """
    bases = (_TestCommon,
             _possibly_unimplemented(_TestGetSet, getset),
             _TestSolve,
             _TestInplaceArithmetic,
             _TestArithmetic,
             _possibly_unimplemented(_TestSlicing, slicing),
             _possibly_unimplemented(_TestSlicingAssign, slicing_assign),
             _possibly_unimplemented(_TestFancyIndexing, fancy_indexing),
             _possibly_unimplemented(_TestFancyIndexingAssign,
                                     fancy_assign),
             _possibly_unimplemented(_TestFancyMultidim,
                                     fancy_indexing and fancy_multidim_indexing),
             _possibly_unimplemented(_TestFancyMultidimAssign,
                                     fancy_multidim_assign and fancy_assign),
             _possibly_unimplemented(_TestMinMax, minmax))

    # check that test names do not clash
    names = {}
    for cls in bases:
        for name in cls.__dict__:
            if not name.startswith('test_'):
                continue
            old_cls = names.get(name)
            if old_cls is not None:
                raise ValueError("Test class %s overloads test %s defined in %s" % (
                    cls.__name__, name, old_cls.__name__))
            names[name] = cls

    return type("TestBase", bases, {})


#------------------------------------------------------------------------------
# Matrix class based tests
#------------------------------------------------------------------------------

class TestCSR(sparse_test_class()):
    spmatrix = csr_matrix
    checked_dtypes = [np.bool_, np.int_, np.float_, np.complex_]

    def test_constructor1(self):
        b = matrix([[0,4,0],
                   [3,0,0],
                   [0,2,0]],'d')
        bsp = csr_matrix(b)
        assert_array_almost_equal(bsp.data,[4,3,2])
        assert_array_equal(bsp.indices,[1,0,1])
        assert_array_equal(bsp.indptr,[0,1,2,3])
        assert_equal(bsp.getnnz(),3)
        assert_equal(bsp.getformat(),'csr')
        assert_array_equal(bsp.todense(),b)

    def test_constructor2(self):
        b = zeros((6,6),'d')
        b[3,4] = 5
        bsp = csr_matrix(b)
        assert_array_almost_equal(bsp.data,[5])
        assert_array_equal(bsp.indices,[4])
        assert_array_equal(bsp.indptr,[0,0,0,0,1,1,1])
        assert_array_almost_equal(bsp.todense(),b)

    def test_constructor3(self):
        b = matrix([[1,0],
                   [0,2],
                   [3,0]],'d')
        bsp = csr_matrix(b)
        assert_array_almost_equal(bsp.data,[1,2,3])
        assert_array_equal(bsp.indices,[0,1,0])
        assert_array_equal(bsp.indptr,[0,1,2,3])
        assert_array_almost_equal(bsp.todense(),b)

### currently disabled
##    def test_constructor4(self):
##        """try using int64 indices"""
##        data = arange( 6 ) + 1
##        col = array( [1, 2, 1, 0, 0, 2], dtype='int64' )
##        ptr = array( [0, 2, 4, 6], dtype='int64' )
##
##        a = csr_matrix( (data, col, ptr), shape = (3,3) )
##
##        b = matrix([[0,1,2],
##                    [4,3,0],
##                    [5,0,6]],'d')
##
##        assert_equal(a.indptr.dtype,numpy.dtype('int64'))
##        assert_equal(a.indices.dtype,numpy.dtype('int64'))
##        assert_array_equal(a.todense(),b)

    def test_constructor4(self):
        # using (data, ij) format
        row = array([2, 3, 1, 3, 0, 1, 3, 0, 2, 1, 2])
        col = array([0, 1, 0, 0, 1, 1, 2, 2, 2, 2, 1])
        data = array([6., 10., 3., 9., 1., 4.,
                              11., 2., 8., 5., 7.])

        ij = vstack((row,col))
        csr = csr_matrix((data,ij),(4,3))
        assert_array_equal(arange(12).reshape(4,3),csr.todense())

    def test_constructor5(self):
        # infer dimensions from arrays
        indptr = array([0,1,3,3])
        indices = array([0,5,1,2])
        data = array([1,2,3,4])
        csr = csr_matrix((data, indices, indptr))
        assert_array_equal(csr.shape,(3,6))

    def test_sort_indices(self):
        data = arange(5)
        indices = array([7, 2, 1, 5, 4])
        indptr = array([0, 3, 5])
        asp = csr_matrix((data, indices, indptr), shape=(2,10))
        bsp = asp.copy()
        asp.sort_indices()
        assert_array_equal(asp.indices,[1, 2, 7, 4, 5])
        assert_array_equal(asp.todense(),bsp.todense())

    def test_eliminate_zeros(self):
        data = array([1, 0, 0, 0, 2, 0, 3, 0])
        indices = array([1, 2, 3, 4, 5, 6, 7, 8])
        indptr = array([0, 3, 8])
        asp = csr_matrix((data, indices, indptr), shape=(2,10))
        bsp = asp.copy()
        asp.eliminate_zeros()
        assert_array_equal(asp.nnz, 3)
        assert_array_equal(asp.data,[1, 2, 3])
        assert_array_equal(asp.todense(),bsp.todense())

    def test_ufuncs(self):
        X = csr_matrix(np.arange(20).reshape(4, 5) / 20.)
        for f in ["sin", "tan", "arcsin", "arctan", "sinh", "tanh",
                  "arcsinh", "arctanh", "rint", "sign", "expm1", "log1p",
                  "deg2rad", "rad2deg", "floor", "ceil", "trunc", "sqrt"]:
            assert_equal(hasattr(csr_matrix, f), True)
            X2 = getattr(X, f)()
            assert_equal(X.shape, X2.shape)
            assert_array_equal(X.indices, X2.indices)
            assert_array_equal(X.indptr, X2.indptr)
            assert_array_equal(X2.toarray(), getattr(np, f)(X.toarray()))

    def test_unsorted_arithmetic(self):
        data = arange(5)
        indices = array([7, 2, 1, 5, 4])
        indptr = array([0, 3, 5])
        asp = csr_matrix((data, indices, indptr), shape=(2,10))
        data = arange(6)
        indices = array([8, 1, 5, 7, 2, 4])
        indptr = array([0, 2, 6])
        bsp = csr_matrix((data, indices, indptr), shape=(2,10))
        assert_equal((asp + bsp).todense(), asp.todense() + bsp.todense())

    def test_fancy_indexing_broadcast(self):
        # broadcasting indexing mode is supported
        I = np.array([[1], [2], [3]])
        J = np.array([3, 4, 2])

        np.random.seed(1234)
        D = np.asmatrix(np.random.rand(5, 7))
        S = self.spmatrix(D)

        SIJ = S[I,J]
        if isspmatrix(SIJ):
            SIJ = SIJ.todense()
        assert_equal(SIJ, D[I,J])


class TestCSC(sparse_test_class()):
    spmatrix = csc_matrix
    checked_dtypes = [np.bool_, np.int_, np.float_, np.complex_]

    def test_constructor1(self):
        b = matrix([[1,0,0,0],[0,0,1,0],[0,2,0,3]],'d')
        bsp = csc_matrix(b)
        assert_array_almost_equal(bsp.data,[1,2,1,3])
        assert_array_equal(bsp.indices,[0,2,1,2])
        assert_array_equal(bsp.indptr,[0,1,2,3,4])
        assert_equal(bsp.getnnz(),4)
        assert_equal(bsp.shape,b.shape)
        assert_equal(bsp.getformat(),'csc')

    def test_constructor2(self):
        b = zeros((6,6),'d')
        b[2,4] = 5
        bsp = csc_matrix(b)
        assert_array_almost_equal(bsp.data,[5])
        assert_array_equal(bsp.indices,[2])
        assert_array_equal(bsp.indptr,[0,0,0,0,0,1,1])

    def test_constructor3(self):
        b = matrix([[1,0],[0,0],[0,2]],'d')
        bsp = csc_matrix(b)
        assert_array_almost_equal(bsp.data,[1,2])
        assert_array_equal(bsp.indices,[0,2])
        assert_array_equal(bsp.indptr,[0,1,2])

    def test_constructor4(self):
        # using (data, ij) format
        row = array([2, 3, 1, 3, 0, 1, 3, 0, 2, 1, 2])
        col = array([0, 1, 0, 0, 1, 1, 2, 2, 2, 2, 1])
        data = array([6., 10., 3., 9., 1., 4.,
                              11., 2., 8., 5., 7.])

        ij = vstack((row,col))
        csc = csc_matrix((data,ij),(4,3))
        assert_array_equal(arange(12).reshape(4,3),csc.todense())

    def test_constructor5(self):
        # infer dimensions from arrays
        indptr = array([0,1,3,3])
        indices = array([0,5,1,2])
        data = array([1,2,3,4])
        csc = csc_matrix((data, indices, indptr))
        assert_array_equal(csc.shape,(6,3))

    def test_eliminate_zeros(self):
        data = array([1, 0, 0, 0, 2, 0, 3, 0])
        indices = array([1, 2, 3, 4, 5, 6, 7, 8])
        indptr = array([0, 3, 8])
        asp = csc_matrix((data, indices, indptr), shape=(10,2))
        bsp = asp.copy()
        asp.eliminate_zeros()
        assert_array_equal(asp.nnz, 3)
        assert_array_equal(asp.data,[1, 2, 3])
        assert_array_equal(asp.todense(),bsp.todense())

    def test_sort_indices(self):
        data = arange(5)
        row = array([7, 2, 1, 5, 4])
        ptr = [0, 3, 5]
        asp = csc_matrix((data, row, ptr), shape=(10,2))
        bsp = asp.copy()
        asp.sort_indices()
        assert_array_equal(asp.indices,[1, 2, 7, 4, 5])
        assert_array_equal(asp.todense(),bsp.todense())

    def test_ufuncs(self):
        X = csc_matrix(np.arange(21).reshape(7, 3) / 21.)
        for f in ["sin", "tan", "arcsin", "arctan", "sinh", "tanh",
                  "arcsinh", "arctanh", "rint", "sign", "expm1", "log1p",
                  "deg2rad", "rad2deg", "floor", "ceil", "trunc", "sqrt"]:
            assert_equal(hasattr(csr_matrix, f), True)
            X2 = getattr(X, f)()
            assert_equal(X.shape, X2.shape)
            assert_array_equal(X.indices, X2.indices)
            assert_array_equal(X.indptr, X2.indptr)
            assert_array_equal(X2.toarray(), getattr(np, f)(X.toarray()))

    def test_unsorted_arithmetic(self):
        data = arange(5)
        indices = array([7, 2, 1, 5, 4])
        indptr = array([0, 3, 5])
        asp = csc_matrix((data, indices, indptr), shape=(10,2))
        data = arange(6)
        indices = array([8, 1, 5, 7, 2, 4])
        indptr = array([0, 2, 6])
        bsp = csc_matrix((data, indices, indptr), shape=(10,2))
        assert_equal((asp + bsp).todense(), asp.todense() + bsp.todense())

    def test_fancy_indexing_broadcast(self):
        # broadcasting indexing mode is supported
        I = np.array([[1], [2], [3]])
        J = np.array([3, 4, 2])

        np.random.seed(1234)
        D = np.asmatrix(np.random.rand(5, 7))
        S = self.spmatrix(D)

        SIJ = S[I,J]
        if isspmatrix(SIJ):
            SIJ = SIJ.todense()
        assert_equal(SIJ, D[I,J])


class TestDOK(sparse_test_class(slicing=False,
                                slicing_assign=False,
                                fancy_indexing=False,
                                fancy_assign=False,
                                minmax=False)):
    spmatrix = dok_matrix
    checked_dtypes = [np.int_, np.float_, np.complex_]

    def test_mult(self):
        A = dok_matrix((10,10))
        A[0,3] = 10
        A[5,6] = 20
        D = A*A.T
        E = A*A.H
        assert_array_equal(D.A, E.A)

    def test_add_nonzero(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SparseEfficiencyWarning)
            A = self.spmatrix((3,2))
            A[0,1] = -10
            A[2,0] = 20
            A = A + 10
            B = matrix([[10, 0], [10, 10], [30, 10]])
            assert_array_equal(A.todense(), B)

            A = A + 1j
            B = B + 1j
            assert_array_equal(A.todense(), B)

    def test_dok_divide_scalar(self):
        A = self.spmatrix((3,2))
        A[0,1] = -10
        A[2,0] = 20

        assert_array_equal((A/1j).todense(), A.todense()/1j)
        assert_array_equal((A/9).todense(), A.todense()/9)

    def test_convert(self):
        # Test provided by Andrew Straw.  Fails in SciPy <= r1477.
        (m, n) = (6, 7)
        a = dok_matrix((m, n))

        # set a few elements, but none in the last column
        a[2,1] = 1
        a[0,2] = 2
        a[3,1] = 3
        a[1,5] = 4
        a[4,3] = 5
        a[4,2] = 6

        # assert that the last column is all zeros
        assert_array_equal(a.toarray()[:,n-1], zeros(m,))

        # make sure it still works for CSC format
        csc = a.tocsc()
        assert_array_equal(csc.toarray()[:,n-1], zeros(m,))

        # now test CSR
        (m, n) = (n, m)
        b = a.transpose()
        assert_equal(b.shape, (m, n))
        # assert that the last row is all zeros
        assert_array_equal(b.toarray()[m-1,:], zeros(n,))

        # make sure it still works for CSR format
        csr = b.tocsr()
        assert_array_equal(csr.toarray()[m-1,:], zeros(n,))

    def test_ctor(self):
        caught = 0
        # Empty ctor
        assert_raises(TypeError, dok_matrix)

        # Dense ctor
        b = matrix([[1,0,0,0],[0,0,1,0],[0,2,0,3]],'d')
        A = dok_matrix(b)
        assert_equal(b.dtype, A.dtype)
        assert_equal(A.todense(), b)

        # Sparse ctor
        c = csr_matrix(b)
        assert_equal(A.todense(), c.todense())

        data = [[0, 1, 2], [3, 0, 0]]
        d = dok_matrix(data, dtype=np.float32)
        assert_equal(d.dtype, np.float32)
        da = d.toarray()
        assert_equal(da.dtype, np.float32)
        assert_array_equal(da, data)

    def test_resize(self):
        # A couple basic tests of the resize() method.
        #
        # resize(shape) resizes the array in-place.
        a = dok_matrix((5,5))
        a[:,0] = 1
        a.resize((2,2))
        expected1 = array([[1,0],[1,0]])
        assert_array_equal(a.todense(), expected1)
        a.resize((3,2))
        expected2 = array([[1,0],[1,0],[0,0]])
        assert_array_equal(a.todense(), expected2)

    def test_ticket1160(self):
        # Regression test for ticket #1160.
        a = dok_matrix((3,3))
        a[0,0] = 0
        # This assert would fail, because the above assignment would
        # incorrectly call __set_item__ even though the value was 0.
        assert_((0,0) not in a.keys(), "Unexpected entry (0,0) in keys")

        # Slice assignments were also affected.
        b = dok_matrix((3,3))
        b[:,0] = 0
        assert_(len(b.keys()) == 0, "Unexpected entries in keys")

    ##
    ## TODO: The DOK matrix currently returns invalid results rather
    ##       than raising errors in some indexing operations
    ##

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_slice_scalar_assign(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_slice_assign_2(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_indexing(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_add_sub(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_scalar_assign_2(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_assign_ndarray(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_indexing_set(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_assign_list(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_assign_slice(self):
        pass

    @dec.knownfailureif(True, "known deficiency in DOK")
    def test_fancy_indexing_multidim_set(self):
        pass


class TestLIL(sparse_test_class(minmax=False)):
    spmatrix = lil_matrix
    checked_dtypes = [np.int_, np.float_, np.complex_]

    def test_dot(self):
        A = matrix(zeros((10,10)))
        A[0,3] = 10
        A[5,6] = 20

        B = lil_matrix((10,10))
        B[0,3] = 10
        B[5,6] = 20
        assert_array_equal(A * A.T, (B * B.T).todense())
        assert_array_equal(A * A.H, (B * B.H).todense())

    def test_scalar_mul(self):
        x = lil_matrix((3,3))
        x[0,0] = 2

        x = x*2
        assert_equal(x[0,0],4)

        x = x*0
        assert_equal(x[0,0],0)

    def test_reshape(self):
        x = lil_matrix((4,3))
        x[0,0] = 1
        x[2,1] = 3
        x[3,2] = 5
        x[0,2] = 7

        for s in [(12,1),(1,12)]:
            assert_array_equal(x.reshape(s).todense(),
                               x.todense().reshape(s))

    def test_inplace_ops(self):
        A = lil_matrix([[0,2,3],[4,0,6]])
        B = lil_matrix([[0,1,0],[0,2,3]])

        data = {'add': (B,A + B),
                'sub': (B,A - B),
                'mul': (3,A * 3)}

        for op,(other,expected) in data.items():
            result = A.copy()
            getattr(result, '__i%s__' % op)(other)

            assert_array_equal(result.todense(), expected.todense())

        # Ticket 1604.
        A = lil_matrix((1,3), dtype=np.dtype('float64'))
        B = array([0.1,0.1,0.1])
        A[0,:] += B
        assert_array_equal(A[0,:].toarray().squeeze(), B)

    def test_lil_iteration(self):
        row_data = [[1,2,3],[4,5,6]]
        B = lil_matrix(array(row_data))
        for r,row in enumerate(B):
            assert_array_equal(row.todense(),array(row_data[r],ndmin=2))

    def test_lil_from_csr(self):
        # Tests whether a lil_matrix can be constructed from a
        # csr_matrix.
        B = lil_matrix((10,10))
        B[0,3] = 10
        B[5,6] = 20
        B[8,3] = 30
        B[3,8] = 40
        B[8,9] = 50
        C = B.tocsr()
        D = lil_matrix(C)
        assert_array_equal(C.A, D.A)

    def test_fancy_indexing_lil(self):
        M = asmatrix(arange(25).reshape(5,5))
        A = lil_matrix(M)

        assert_equal(A[array([1,2,3]),2:3].todense(), M[array([1,2,3]),2:3])

    def test_point_wise_multiply(self):
        l = lil_matrix((4,3))
        l[0,0] = 1
        l[1,1] = 2
        l[2,2] = 3
        l[3,1] = 4

        m = lil_matrix((4,3))
        m[0,0] = 1
        m[0,1] = 2
        m[2,2] = 3
        m[3,1] = 4
        m[3,2] = 4

        assert_array_equal(l.multiply(m).todense(),
                           m.multiply(l).todense())

        assert_array_equal(l.multiply(m).todense(),
                           [[1,0,0],
                            [0,0,0],
                            [0,0,9],
                            [0,16,0]])

    def test_lil_multiply_removal(self):
        # Ticket #1427.
        a = lil_matrix(np.ones((3,3)))
        a *= 2.
        a[0, :] = 0


class TestCOO(sparse_test_class(getset=False,
                                slicing=False, slicing_assign=False,
                                fancy_indexing=False, fancy_assign=False)):
    spmatrix = coo_matrix
    checked_dtypes = [np.int_, np.float_, np.complex_]

    def test_constructor1(self):
        # unsorted triplet format
        row = array([2, 3, 1, 3, 0, 1, 3, 0, 2, 1, 2])
        col = array([0, 1, 0, 0, 1, 1, 2, 2, 2, 2, 1])
        data = array([6., 10., 3., 9., 1., 4.,
                              11., 2., 8., 5., 7.])

        coo = coo_matrix((data,(row,col)),(4,3))

        assert_array_equal(arange(12).reshape(4,3),coo.todense())

    def test_constructor2(self):
        # unsorted triplet format with duplicates (which are summed)
        row = array([0,1,2,2,2,2,0,0,2,2])
        col = array([0,2,0,2,1,1,1,0,0,2])
        data = array([2,9,-4,5,7,0,-1,2,1,-5])
        coo = coo_matrix((data,(row,col)),(3,3))

        mat = matrix([[4,-1,0],[0,0,9],[-3,7,0]])

        assert_array_equal(mat,coo.todense())

    def test_constructor3(self):
        # empty matrix
        coo = coo_matrix((4,3))

        assert_array_equal(coo.shape,(4,3))
        assert_array_equal(coo.row,[])
        assert_array_equal(coo.col,[])
        assert_array_equal(coo.data,[])
        assert_array_equal(coo.todense(),zeros((4,3)))

    def test_constructor4(self):
        # from dense matrix
        mat = array([[0,1,0,0],
                     [7,0,3,0],
                     [0,4,0,0]])
        coo = coo_matrix(mat)
        assert_array_equal(coo.todense(),mat)

        # upgrade rank 1 arrays to row matrix
        mat = array([0,1,0,0])
        coo = coo_matrix(mat)
        assert_array_equal(coo.todense(),mat.reshape(1,-1))

    # COO does not have a __getitem__ to support iteration
    def test_iterator(self):
        pass

    def test_todia_all_zeros(self):
        zeros = [[0, 0]]
        dia = coo_matrix(zeros).todia()
        assert_array_equal(dia.A, zeros)


class TestDIA(sparse_test_class(getset=False, slicing=False, slicing_assign=False,
                                fancy_indexing=False, fancy_assign=False,
                                minmax=False)):
    spmatrix = dia_matrix
    checked_dtypes = [np.int_, np.float_, np.complex_]

    def test_constructor1(self):
        D = matrix([[1, 0, 3, 0],
                    [1, 2, 0, 4],
                    [0, 2, 3, 0],
                    [0, 0, 3, 4]])
        data = np.array([[1,2,3,4]]).repeat(3,axis=0)
        offsets = np.array([0,-1,2])
        assert_equal(dia_matrix((data,offsets), shape=(4,4)).todense(), D)

    # DIA does not have a __getitem__ to support iteration
    def test_iterator(self):
        pass


class TestBSR(sparse_test_class(getset=False,
                                slicing=False, slicing_assign=False,
                                fancy_indexing=False, fancy_assign=False)):
    spmatrix = bsr_matrix
    checked_dtypes = [np.int_, np.float_, np.complex_]

    def test_constructor1(self):
        # check native BSR format constructor
        indptr = array([0,2,2,4])
        indices = array([0,2,2,3])
        data = zeros((4,2,3))

        data[0] = array([[0, 1, 2],
                         [3, 0, 5]])
        data[1] = array([[0, 2, 4],
                         [6, 0, 10]])
        data[2] = array([[0, 4, 8],
                         [12, 0, 20]])
        data[3] = array([[0, 5, 10],
                         [15, 0, 25]])

        A = kron([[1,0,2,0],[0,0,0,0],[0,0,4,5]], [[0,1,2],[3,0,5]])
        Asp = bsr_matrix((data,indices,indptr),shape=(6,12))
        assert_equal(Asp.todense(),A)

        # infer shape from arrays
        Asp = bsr_matrix((data,indices,indptr))
        assert_equal(Asp.todense(),A)

    def test_constructor2(self):
        # construct from dense

        # test zero mats
        for shape in [(1,1), (5,1), (1,10), (10,4), (3,7), (2,1)]:
            A = zeros(shape)
            assert_equal(bsr_matrix(A).todense(),A)
        A = zeros((4,6))
        assert_equal(bsr_matrix(A,blocksize=(2,2)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(2,3)).todense(),A)

        A = kron([[1,0,2,0],[0,0,0,0],[0,0,4,5]], [[0,1,2],[3,0,5]])
        assert_equal(bsr_matrix(A).todense(),A)
        assert_equal(bsr_matrix(A,shape=(6,12)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(1,1)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(2,3)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(2,6)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(2,12)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(3,12)).todense(),A)
        assert_equal(bsr_matrix(A,blocksize=(6,12)).todense(),A)

        A = kron([[1,0,2,0],[0,1,0,0],[0,0,0,0]], [[0,1,2],[3,0,5]])
        assert_equal(bsr_matrix(A,blocksize=(2,3)).todense(),A)

    def test_eliminate_zeros(self):
        data = kron([1, 0, 0, 0, 2, 0, 3, 0], [[1,1],[1,1]]).T
        data = data.reshape(-1,2,2)
        indices = array([1, 2, 3, 4, 5, 6, 7, 8])
        indptr = array([0, 3, 8])
        asp = bsr_matrix((data, indices, indptr), shape=(4,20))
        bsp = asp.copy()
        asp.eliminate_zeros()
        assert_array_equal(asp.nnz, 3*4)
        assert_array_equal(asp.todense(),bsp.todense())

    def test_bsr_matvec(self):
        A = bsr_matrix(arange(2*3*4*5).reshape(2*4,3*5), blocksize=(4,5))
        x = arange(A.shape[1]).reshape(-1,1)
        assert_equal(A*x, A.todense()*x)

    def test_bsr_matvecs(self):
        A = bsr_matrix(arange(2*3*4*5).reshape(2*4,3*5), blocksize=(4,5))
        x = arange(A.shape[1]*6).reshape(-1,6)
        assert_equal(A*x, A.todense()*x)

    @dec.knownfailureif(True, "BSR not implemented")
    def test_iterator(self):
        pass


if __name__ == "__main__":
    run_module_suite()
