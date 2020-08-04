import numpy

from scipy import interpolate
from scipy import spatial

import matplotlib.pylab as plt
import matplotlib as mpl

from srxraylib.plot.gol import plot_image, set_qt, plot

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

from oasys.util.oasys_util import write_surface_file

def write_generic_h5_surface(s, xx, yy, filename='presurface.hdf5',subgroup_name="surface_file"):
    # import h5py
    # file = h5py.File(filename, 'w')
    # file[subgroup_name + "/X"] = xx
    # file[subgroup_name + "/Y"] = yy
    # file[subgroup_name + "/Z"] = s.T
    # file.close()
    # print("write_h5_surface: File for OASYS " + filename + " written to disk.")
    write_surface_file(s.T, xx, yy, filename, overwrite=True)
    print("write_h5_surface: File for OASYS " + filename + " written to disk.")


class FEA_File():
    def __init__(self,filename=""):
        self.filename = filename
        self.reset()

    def reset(self):
        self.Xundeformed = None  # 1D array
        self.Yundeformed = None  # 1D array
        self.Zundeformed = None  # 1D array

        self.Xdeformation = None  # 1D array
        self.Ydeformation = None  # 1D array
        self.Zdeformation = None  # 1D array

        self.triPi = None
        self.tri = None

        self.x_interpolated = None  # 1D array
        self.y_interpolated = None  # 1D array
        self.Z_INTERPOLATED = None  # 2D array

    @classmethod
    def process_file(cls, filename_in, n_axis_0=301, n_axis_1=51,
                     filename_out="", invert_axes_names=False,
                     detrend=0, # 0=none 1(2)=straight line axis 0 (1), 3(4) best circle axis 0(1)
                     reset_height_method=0,
                     replicate_raw_data_flag=0, # 0=None, 1=axis0, 2=axis1, 3=both axis
                     file_in_type=0,skiprows=0,
                     do_plot=False):

        o1 = FEA_File(filename=filename_in)
        o1.load_multicolumn_file(skiprows=skiprows,file_in_type=file_in_type)


        o1.replicate_raw_data(replicate_raw_data_flag)



        o1.triangulate()

        if do_plot:
            o1.plot_triangulation()

        o1.interpolate(n_axis_0, n_axis_1)
        if do_plot:
            o1.plot_interpolated()

        if o1.does_interpolated_have_nan():
            o1.remove_borders_in_interpolated_data()

        if do_plot:
            o1.plot_surface_image()

        if detrend == 0:
            pass
        elif detrend == 1:
            o1.detrend_straight_line(axis=0)
        elif detrend == 2:
            o1.detrend_straight_line(axis=1)
        elif detrend == 3:
            o1.detrend_best_circle(axis=0)
        elif detrend == 5:
            o1.detrend_best_circle(axis=1)

        # o1.reset_height_to_minimum()

        if reset_height_method == 0:
            pass
        elif reset_height_method == 1:
            o1.reset_height_to_minimum()
        elif reset_height_method == 2:
            o1.reset_height_to_central_value()

        if do_plot:
            o1.plot_surface_image()

        if filename_out != "":
            o1.write_h5_surface(filename=filename_out, invert_axes_names=invert_axes_names)

        return o1

    def set_filename(self,filename):
        self.filename = filename

    def load_multicolumn_file(self,skiprows=0,factorX=1.0,factorY=1.0,factorZ=1.0,file_in_type=0):
        if file_in_type == 0: # ALS
            node = numpy.loadtxt(self.filename, skiprows=skiprows, dtype=numpy.float64)

            # Coordinates
            self.Xundeformed = factorX * node[:, 1]  # X=x in m
            self.Yundeformed = factorY * node[:, 2]  # Y=z in m
            self.Zundeformed = factorZ * node[:, 3]  # Z=uy vertical displacement in m

            self.Xdeformation = factorX * node[:, 4]  # X=x in m
            self.Ydeformation = factorY * node[:, 5]  # Y=z in m
            self.Zdeformation = factorZ * node[:, 6]  # Z=uy vertical displacement in m
        elif file_in_type == 1: # ESRF
            node = numpy.loadtxt(self.filename, skiprows=skiprows, dtype=numpy.float64, delimiter=',')

            # Coordinates
            self.Xundeformed = factorX * node[:, 0]  # X=x in m
            self.Yundeformed = factorY * node[:, 1]  # Y=z in m
            self.Zundeformed = factorZ * node[:, 2]  # Z=uy vertical displacement in m

            self.Xdeformation = factorX * node[:, 3]  # X=x in m
            self.Ydeformation = factorY * node[:, 4]  # Y=z in m
            self.Zdeformation = factorZ * node[:, 5]  # Z=uy vertical displacement in m

    def Xdeformed(self):
        return self.Xundeformed + self.Xdeformation

    def Ydeformed(self):
        return self.Yundeformed + self.Ydeformation

    def Zdeformed(self):
        return self.Zundeformed + self.Zdeformation


    def get_deformed(self):
        return self.Xdeformed(),self.Ydeformed(),self.Zdeformed()

    def get_undeformed(self):
        return self.Xundeformed,self.Yundeformed,self.Zundeformed

    def get_deformation(self):
        return self.Xdeformation,self.Ydeformation,self.Zdeformation

    def get_limits_undeformed(self):

        print("X undeformed limits: ", self.Xundeformed.min(), self.Xundeformed.max())
        print("Y undeformed limits: ", self.Yundeformed.min(), self.Yundeformed.max())
        print("Z undeformed limits: ", self.Zundeformed.min(), self.Zundeformed.max())

        return self.Xundeformed.min(), self.Xundeformed.max(), \
               self.Yundeformed.min(), self.Yundeformed.max(), \
               self.Zundeformed.min(), self.Zundeformed.max()

    def get_limits_deformation(self):

        print("Xdeformation limits: ", self.Xdeformation.min(), self.Xdeformation.max())
        print("Ydeformation limits: ", self.Ydeformation.min(), self.Ydeformation.max())
        print("Zdeformation limits: ", self.Zdeformation.min(), self.Zdeformation.max())

        return self.Xdeformation.min(), self.Xdeformation.max(), \
               self.Ydeformation.min(), self.Ydeformation.max(), \
               self.Zdeformation.min(), self.Zdeformation.max()

    def get_limits_deformed(self):

        print("X deformed limits: ", self.Xdeformed().min(), self.Xdeformed().max())
        print("Y deformed limits: ", self.Ydeformed().min(), self.Ydeformed().max())
        print("Z deformed limits: ", self.Zdeformed().min(), self.Zdeformed().max())

        return self.Xdeformed().min(), self.Xdeformed().max(), \
               self.Ydeformed().min(), self.Ydeformed().max(), \
               self.Zdeformed().min(), self.Zdeformed().max()


    def replicate_raw_data(self,flag):

        if flag == 0: # nothing
            return
        elif flag == 1: # axis 0
            self.Xundeformed = numpy.concatenate((-self.Xundeformed, self.Xundeformed))
            self.Yundeformed = numpy.concatenate((self.Yundeformed, self.Yundeformed))
            self.Zundeformed = numpy.concatenate((self.Zundeformed, self.Zundeformed))
            self.Xdeformation = numpy.concatenate((-self.Xdeformation, self.Xdeformation))
            self.Ydeformation = numpy.concatenate((self.Ydeformation, self.Ydeformation))
            self.Zdeformation = numpy.concatenate((self.Zdeformation, self.Zdeformation))
        elif flag == 2: # axis 1
            self.Xundeformed = numpy.concatenate((self.Xundeformed, self.Xundeformed))
            self.Yundeformed = numpy.concatenate((-self.Yundeformed, self.Yundeformed))
            self.Zundeformed = numpy.concatenate((self.Zundeformed, self.Zundeformed))
            self.Xdeformation = numpy.concatenate((self.Xdeformation, self.Xdeformation))
            self.Ydeformation = numpy.concatenate((-self.Ydeformation, self.Ydeformation))
            self.Zdeformation = numpy.concatenate((self.Zdeformation, self.Zdeformation))
        elif flag == 3: # both axes
            self.Xundeformed = numpy.concatenate((-self.Xundeformed, self.Xundeformed))
            self.Yundeformed = numpy.concatenate((self.Yundeformed, self.Yundeformed))
            self.Zundeformed = numpy.concatenate((self.Zundeformed, self.Zundeformed))
            self.Xdeformation = numpy.concatenate((-self.Xdeformation, self.Xdeformation))
            self.Ydeformation = numpy.concatenate((self.Ydeformation, self.Ydeformation))
            self.Zdeformation = numpy.concatenate((self.Zdeformation, self.Zdeformation))

            self.Xundeformed = numpy.concatenate((self.Xundeformed, self.Xundeformed))
            self.Yundeformed = numpy.concatenate((-self.Yundeformed, self.Yundeformed))
            self.Zundeformed = numpy.concatenate((self.Zundeformed, self.Zundeformed))
            self.Xdeformation = numpy.concatenate((self.Xdeformation, self.Xdeformation))
            self.Ydeformation = numpy.concatenate((-self.Ydeformation, self.Ydeformation))
            self.Zdeformation = numpy.concatenate((self.Zdeformation, self.Zdeformation))


    def triangulate(self):
        # triangulation
        self.triPi = numpy.array([self.Xdeformed(), self.Ydeformed()]).transpose()
        self.tri = spatial.Delaunay(self.triPi)

    def plot_triangulation(self,show=True):
        fig = plt.figure()
        plt.triplot(self.Xdeformed(), self.Ydeformed() , self.tri.simplices.copy())
        plt.plot(self.Xdeformed(), self.Ydeformed(), "or", label = "Data")
        plt.grid()
        plt.legend()
        plt.title("triangulation")
        plt.xlabel("x")
        plt.ylabel("y")
        if show:
            plt.show()
        return fig

    def get_Xinterpolated_mesh(self):
        return numpy.outer(self.x_interpolated,numpy.ones_like(self.y_interpolated))

    def get_Yinterpolated_mesh(self):
        return numpy.outer(numpy.ones_like(self.x_interpolated),self.y_interpolated)


    def interpolate(self,nx,ny,remove_nan=0):
        """

        :param nx:
        :param ny:
        :param remove_nan: 0=No, 1=Yes (replace with minimum height) 2=Yes (replace with 0)
        :return:
        """
        if self.tri is None:
            self.triangulate()

        lim = self.get_limits_deformed()
        self.x_interpolated = numpy.linspace(lim[0],lim[1],nx)
        self.y_interpolated = numpy.linspace(lim[2],lim[3],ny)

        X_INTERPOLATED =  self.get_Xinterpolated_mesh()
        Y_INTERPOLATED =  self.get_Yinterpolated_mesh()

        self.P = numpy.array([X_INTERPOLATED.flatten(), Y_INTERPOLATED.flatten() ]).transpose()

        if remove_nan ==2:
            self.Z_INTERPOLATED = interpolate.griddata(self.triPi, self.Zdeformed(), self.P, rescale=True, method = "cubic", fill_value=0.0 ).reshape([nx,ny])
        elif remove_nan ==1:
            self.Z_INTERPOLATED = interpolate.griddata(self.triPi, self.Zdeformed(), self.P, rescale=True, method = "cubic", fill_value=self.Zdeformed().min() ).reshape([nx,ny])
        elif remove_nan == 0:
            self.Z_INTERPOLATED = interpolate.griddata(self.triPi, self.Zdeformed(), self.P, rescale=True, method="cubic").reshape([nx, ny])


    def plot_interpolated(self, show=True):
        fig = plt.figure()
        plt.contourf(self.get_Xinterpolated_mesh(), self.get_Yinterpolated_mesh(), self.Z_INTERPOLATED, 50, cmap = mpl.cm.jet)
        plt.colorbar()
        plt.contour(self.get_Xinterpolated_mesh(), self.get_Yinterpolated_mesh(), self.Z_INTERPOLATED, 20, colors = "k")
        plt.plot(self.Xdeformed(), self.Ydeformed(), "or", label = "Data")
        plt.legend()
        # plt.title = "Interpolated"  <---- THIS MAKES ERROR IN THE NEXT PLOT!!!!!!!!!!!!!!!!!
        plt.grid()
        if show:
            plt.show()
        return fig



    def plot_surface_image(self,invert_axes_names=False):
        if invert_axes_names:
            plot_image(self.Z_INTERPOLATED,self.x_interpolated,self.y_interpolated ,title="file: %s, axes names INVERTED from ANSYS"%self.filename,
                       xtitle="Y (%d pixels, max:%f)"%(self.x_interpolated.size,self.x_interpolated.max()),
                       ytitle="X (%d pixels, max:%f)"%(self.y_interpolated.size,self.y_interpolated.max()) )
        else:
            plot_image(self.Z_INTERPOLATED,self.x_interpolated,self.y_interpolated,title="file: %s, axes as in ANSYS"%self.filename,
                       xtitle="X (%d pixels, max:%f)"%(self.x_interpolated.size,self.x_interpolated.max()),
                       ytitle="Y (%d pixels, max:%f)"%(self.y_interpolated.size,self.y_interpolated.max()) )


    def does_interpolated_have_nan(self):
        return numpy.isnan(self.Z_INTERPOLATED).sum() > 0

    def remove_borders_in_interpolated_data(self):
        self.x_interpolated = self.x_interpolated[1:-2].copy()
        self.y_interpolated = self.y_interpolated[1:-2].copy()
        self.Z_INTERPOLATED = self.Z_INTERPOLATED[1:-2,1:-2].copy()

    def detrend_straight_line(self,axis=0,fitting_domain_ratio=0.5):
        if axis == 0:
            xm = self.x_interpolated.copy()
            zm = self.Z_INTERPOLATED[:,self.y_interpolated.size//2]
        elif axis == 1:
            xm = self.y_interpolated.copy()
            zm = self.Z_INTERPOLATED[self.x_interpolated.size // 2, :]

        zm.shape = -1

        icut = numpy.argwhere( numpy.abs(xm) < (numpy.max((-xm[0],xm[-1])) * fitting_domain_ratio))
        if len(icut) <=5:
            raise Exception("Not enough points for fitting.")

        xcut = xm[icut]
        zmcut = zm[icut]

        xcut.shape = -1
        zmcut.shape = -1

        # plot(xcut, zmcut, xm, zm, legend=["cut", "original"])

        print( numpy.argwhere(numpy.isnan(self.Z_INTERPOLATED)) )
        print("Fitting interval: [%g,%g]" % (xcut[0],xcut[-1]))

        coeff = numpy.polyfit(xcut.copy(), zmcut.copy(), deg=1)

        zfit = coeff[0] * xm  + coeff[1]

        print("Detrending straight line (axis=%d): zfit = %g * coordinate + %g " % (axis, coeff[1], coeff[0]))

        # plot(xcut, zmcut, xm, zfit, legend=["data","fit"])
        # plot(xcut, zmcut, xm, zfit, legend=["cut","fit"],yrange=[-0.000015,0.000005])

        if axis ==0:
            for i in range(self.Z_INTERPOLATED.shape[1]):
                self.Z_INTERPOLATED[:,i] -= zfit
        elif axis == 1:
            for i in range(self.Z_INTERPOLATED.shape[0]):
                self.Z_INTERPOLATED[i,:] -= zfit

    def detrend_best_circle(self,axis=0,fitting_domain_ratio=0.5):
        if axis == 0:
            xm = self.x_interpolated.copy()
            zm = self.Z_INTERPOLATED[:,self.y_interpolated.size//2]
        elif axis == 1:
            xm = self.y_interpolated.copy()
            zm = self.Z_INTERPOLATED[self.x_interpolated.size // 2, :]

        zm.shape = -1

        # icut = numpy.argwhere( numpy.abs(xm) < (numpy.max((-xm[0],xm[-1])) * fitting_domain_ratio))
        icut = numpy.argwhere(numpy.abs(xm) <= fitting_domain_ratio)
        if len(icut) <=5:
            raise Exception("Not enough points for fitting.")

        xcut = xm[icut]
        zmcut = zm[icut]

        xcut.shape = -1
        zmcut.shape = -1

        # plot(xcut, zmcut, xm, zm, legend=["cut", "original"])

        print( numpy.argwhere(numpy.isnan(self.Z_INTERPOLATED)) )
        print("Fitting interval: [%g,%g] (using %d points)" % (xcut[0],xcut[-1],xcut.size))

        coeff = numpy.polyfit(xcut, numpy.gradient(zmcut,xcut), deg=1)

        # zfit = coeff[0] * xm  + coeff[1]
        radius = 1 / coeff[0]
        print("Detrending straight line on sloped (axis=%d): zfit = %g * coordinate + %g " % (axis, coeff[1], coeff[0]))
        print("Radius of curvature: %g m" % (1.0 / coeff[0]))

        if radius >= 0:
            zfit = radius - numpy.sqrt(radius ** 2 - xm ** 2)
        else:
            zfit = radius + numpy.sqrt(radius ** 2 - xm ** 2)

        # plot(xm, zfit, legend=["fit"])
        # plot(xcut, zmcut, xm, zfit, legend=["cut","fit"],yrange=[-0.000015,0.000005])

        if axis ==0:
            for i in range(self.Z_INTERPOLATED.shape[1]):
                self.Z_INTERPOLATED[:,i] -= zfit
        elif axis == 1:
            for i in range(self.Z_INTERPOLATED.shape[0]):
                self.Z_INTERPOLATED[i,:] -= zfit

        return xm, zfit

    def reset_height_to_minimum(self):
        self.Z_INTERPOLATED -= self.Z_INTERPOLATED.min()

    def reset_height_to_central_value(self):
        self.Z_INTERPOLATED -= self.Z_INTERPOLATED[self.Z_INTERPOLATED.shape[0]//2,self.Z_INTERPOLATED.shape[1]//2]


    def write_h5_surface(self,filename='presurface.hdf5',invert_axes_names=False):
        if invert_axes_names:
            write_generic_h5_surface(self.Z_INTERPOLATED.T, self.y_interpolated, self.x_interpolated, filename=filename)
        else:
            write_generic_h5_surface(self.Z_INTERPOLATED, self.x_interpolated, self.y_interpolated, filename=filename)


    def gaussian_filter(self,sigma_axis0=10,sigma_axis1=10):
        from scipy.ndimage import gaussian_filter
        self.Z_INTERPOLATED = gaussian_filter(self.Z_INTERPOLATED, (sigma_axis0,sigma_axis1),
                        order=0, output=None, mode='nearest', cval=0.0, truncate=4.0)

def surface_plot(xs,ys,zs):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')


    # For each set of style and range settings, plot n random points in the box
    # defined by x in [23, 32], y in [0, 100], z in [zlow, zhigh].
    # for m, zlow, zhigh in [('o', -50, -25), ('^', -30, -5)]:
    for m, zlow, zhigh in [('o', zs.min(), zs.max())]:
        ax.scatter(xs, ys, zs, marker=m)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    plt.show()



if __name__ == "__main__":




    # set_qt()


    # o1 = FEA_File.process_file("/home/manuel/OASYS1.2/alsu-scripts/ANSYS/s4.txt", n_axis_0=301, n_axis_1=51,
    #              filename_out="/home/manuel/Oasys/s4.h5", invert_axes_names=True,
    #              detrend=1, reset_height_method=1, do_plot=False)


    # o1 = FEA_File()
    # o1.set_filename("C:/Users/Manuel/Oasys/dispCOSMIC_M1_H_XOPPY.txt")
    # o1.load_multicolumn_file()
    #
    # X,Y,Z = o1.get_deformed()
    # # X, Y, Z = o1.get_undeformed()
    # surface_plot( X,Y,Z)









    # o1.plot_triangulation()
    # o1.plot_interpolated()
    # o1.plot_surface_image()

    o1 = FEA_File.process_file("C:/Users/Manuel/Oasys/TENDER DCM Performance/disp2000.txt", n_axis_0=801, n_axis_1=801,
                 filename_out="", invert_axes_names=True,
                 detrend=1, reset_height_method=2,
                 replicate_raw_data_flag=3,do_plot=False)
    o1.plot_surface_image()
    # # plot(o1.x_interpolated, o1.Z_INTERPOLATED[:,o1.y_interpolated.size//2]) #, o1.y_interpolated
    # x0, y0, z0 = o1.get_undeformed()
    # x, y, z = o1.get_deformed()
    # X = []
    # Z = []
    # numpy.set_printoptions(precision=17)
    #
    # for i in range(x.size):
    #     if numpy.abs(y[i]) ==0:
    #         X.append(x[i])
    #         Z.append(z[i])
    #         if numpy.abs(x[i]) < 50e-6:
    #             print("line %d x:%g z: %g %g " % (i, x[i], z0[i], z[i]))
    # X = numpy.array(X)
    # Z = numpy.array(Z)
    # plot(X, Z,
    #      o1.x_interpolated, o1.Z_INTERPOLATED[:,o1.y_interpolated.size//2],marker=['.','.'],
    #      linestyle=["",""],legend=["raw","interpolated"],xrange=[-250e-6,1550e-6])




    # o1 = FEA_File.process_file("73water_side_cooled_notches_best_LH.txt", n_axis_0=1001, n_axis_1=101,
    #              filename_out="/home/manuel/Oasys/water_side_cooled_notches_best_LH.h5", invert_axes_names=True,
    #              detrend=1, reset_height_method=2,
    #              replicate_raw_data_flag=3,do_plot=False)
    #
    # o1 = FEA_File.process_file("73water_side_cooled_notches_best_LV.txt", n_axis_0=1001, n_axis_1=101,
    #              filename_out="/home/manuel/Oasys/water_side_cooled_notches_best_LV.h5", invert_axes_names=True,
    #              detrend=0, reset_height_method=0,
    #              replicate_raw_data_flag=3,do_plot=False)

    #
