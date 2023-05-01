import numpy as np
import math
import scipy


'''
Collection utility functions to find the corner reflectors based on intensity peak
'''

def oversample_slc(slc,sampling=1,y=None,x=None):
    '''
    oversample the SLC data
        sampling: oversampling factor
    '''
    
    if y is None:
        y = np.arange(slc.shape[0])
    if x is None:
        x = np.arange(slc.shape[1])

    rows, cols = np.shape(slc)
    _slc = np.fft.fftshift(np.fft.fft2(slc))
    min_row = math.ceil(rows * sampling / 2 - rows / 2)
    max_row = min_row + rows
    min_col = math.ceil(cols * sampling / 2 - cols / 2)
    max_col = min_col + cols
    
    slc_padding = np.zeros((rows * sampling, cols * sampling), dtype=_slc.dtype)    #zero padding
    slc_padding[min_row:max_row,min_col:max_col] = _slc
    slc_ = np.fft.fftshift(slc_padding)
    slcovs = np.fft.ifft2(slc_) * sampling * sampling

    y_orign_step = y[1]-y[0]
    y_ovs_step = y_orign_step/sampling
    x_orign_step = x[1]-x[0]
    x_ovs_step = x_orign_step/sampling

    y = np.arange(y[0],y[-1]+y_orign_step,y_ovs_step)
    x = np.arange(x[0],x[-1]+x_orign_step,x_ovs_step)

    return slcovs,y,x

def findCR(data,y,x,x_bound=[-np.inf,np.inf],y_bound=[-np.inf,np.inf],method="sinc"):
    '''
    Find the location of CR with fitting
    '''
    max_ind = np.argmax(data)
    max_data = data[max_ind]
    
    def _sinc2D(x,x0,y0,a,b,c):
        return c*np.sinc(a*(x[0]-x0))*np.sinc(b*(x[1]-y0))
    
    def _para2D(x,x0,y0,a,b,c,d):
        return a*(x[0]-x0)**2+b*(x[1]-y0)**2+c*(x[0]-x0)*(x[1]-y0)+d

    if method == "sinc":
        # using sinc function for fitting 
        xdata = np.vstack((x,y))
        p0 = [x[max_ind],y[max_ind],0.7,0.7,max_data]
        bounds = ([x_bound[0],y_bound[0],0,0,0],[x_bound[1],y_bound[1],1,1,np.inf])
        popt = scipy.optimize.curve_fit(_sinc2D,xdata,data,p0=p0,bounds=bounds)[0]
        xloc = popt[0]; yloc = popt[1]
    elif method == "para":
        #using paraboloid function for fitting
        xdata = np.vstack((x,y))
        p0 = [x[max_ind],y[max_ind],-1,-1,1,1]
        bounds = ([x_bound[0],y_bound[0],-np.inf,-np.inf,-np.inf,0],[x_bound[1],y_bound[1],0,0,np.inf,np.inf])
        popt = scipy.optimize.curve_fit(_para2D,xdata,data,p0=p0,bounds=bounds)[0]
        xloc = popt[0]; yloc = popt[1]

    return yloc,xloc

def interpolate_correction_layers(xcoor, ycoor, data, method):
    '''
    Interpolate the correction layers
        xcoor: UTM coordinates of the CSLC data along x-axis, shape: (N,)
        ycoor: UTM coordinates of the CSLC data along y-axis, shape: (N,)
        data: Correction layer values
        method: Interpolation method ('nearest', 'linear', 'cubic')
    '''
    
    Xcslc, Ycslc = np.meshgrid(xcoor, ycoor)
    xx = np.linspace(xcoor.min(),xcoor.max(),num=data.shape[1])
    yy = np.linspace(ycoor.min(),ycoor.max(),num=data.shape[0])
    Xdata, Ydata = np.meshgrid(xx,yy)

    # Interpolate
    points = list(zip(Xdata.ravel(), Ydata.ravel()))
    values = data.ravel()

    data_resampl = scipy.interpolate.griddata(points, values, (Xcslc, Ycslc), method=method)

    return np.flipud(data_resampl)

