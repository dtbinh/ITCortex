# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 11:37:11 2015

Ref:
[1] Neilson, Logothesis & Rainer - 2006 - Dissociation between Local Field Potentials & spiking
activity in Macaque Inferior Temporal Cortex reveals diagnosticity based encoding of complex
objects.

[2] Kovacs, Vogels & Orban -1995 - Selectivity of Macaque Inferior Temporal Neurons for Partially
Occluded Shapes.

[3] Oreilly et. al. - 2013 - Recurrent processing during object recognition.

@author: s362khan
"""

import numpy as np
import matplotlib.pyplot as plt
import pickle
from scipy.optimize import curve_fit
from mpl_toolkits.mplot3d import Axes3D


def exponential(x, a):
    return a * np.exp(-a * x)


def sigmoid(x, a, b):
    """ http://computing.dcu.ie/~humphrys/Notes/Neural/sigmoid.html """
    return 1.0 / (1 + np.exp(a*(x-b)))

# Code start ----------------------------------------------------------------------------
plt.ion()

# Fit Diagnosticity data ----------------------------------------------------------------
# Diagnosticity is defined as the ratio of the trail by trail variance of in the diagnostic images
# (at all stimulus sizes) and the total trail by trail variance. If a neuron responded only to the
# diagnostic part, its ratio = 1. While if an image  did not preferentially respond to the
# diagnostic parts its ratio = 0.
#
# The total firing rate of the neuron is computed as a weighted average of the diagnostic tuning
# curve and the non diagnostic tuning curve and use the diagnostic variance as the weight.
#
# In supplementary material Diagnosticity metric was compared to the difference between the net
# firing rates to the diagnostic and non-diagnostic parts. For all cases there was a positive
# correlation. Indicating neurons with higher diagnostic variances fired for more diagnostic
# parts than to non-diagnostic parts.

with open('Neilson2006.pkl', 'rb') as fid:
    data = pickle.load(fid)

''' PDF of Diagnostic variance '''
diagVar = data['diagVariance']

hist, bins = np.histogram(diagVar, bins=np.arange(100, step=1), density=True)

# Clean up zeros
idxs = np.nonzero(hist)
hist = hist[idxs]
bins = bins[idxs]

plt.figure('Diagnostic Variance Distribution')
plt.scatter(bins, hist, label='Original Data')

# Fit the pdf
pOptExp, pCovExp = curve_fit(exponential, bins, hist)
plt.plot(bins, exponential(bins, *pOptExp), label='Exponential a*exp(-ax): a=%f' % pOptExp[0])

# # Plot +- 1 SD around fit
# sigma = np.sqrt(pCovExp[0])
# plt.plot(bins, exponential(bins, pOptExp[0] + sigma), 'k--')
# plt.plot(bins, exponential(bins, pOptExp[0] - sigma), 'k--')

#  Generate Data ------------------------------------------------------------------------
# Given the pdf generate random variables that follow the distribution - inverse CDF
#
# Ref:
# [1] http://www.ece.virginia.edu/mv/edu/prob/stat/random-number-generation.pdf
# [2] SYSD 750 - Lecture Notes
#
# CDF = Fx(x) = y = 1-np.exp(-a*x)
# ln(y-1) = -a*x, and y in uniformly distributed over 0, 1
n = 100

y_arr = np.random.uniform(size=n)
genDiagVar = -np.log(y_arr) / pOptExp[0]

hist, bins = np.histogram(genDiagVar, bins=np.arange(100), density=True)
# Clean up zeros
idxs = np.nonzero(hist)
hist = hist[idxs]
bins = bins[idxs]

plt.figure('Diagnostic Variance Distribution')
plt.scatter(bins, hist, marker='+', color='red', label='Generated Data')
plt.title('Distribution of diagnosticity across IT')
plt.xlabel('Diagnosticity (%)')
plt.ylabel('Probability Density')
plt.legend()

# Diagnostic and Non Diagnostic Tuning Curves ------------------------------------------
#
# Data Problems:
# Neilson 2006 - too few points
# Kovacs 1995  - a little better 4 points, but multiple objects
# Oreilly 2013 - lots more points but not recorded data.
#
# Neilson 2006:
# [1] For the same percentage of area, diagnostic firing rates are always higher than
#     non-diagnostic rates.
# [2] Even though there are variations between the firing rates of individual neurons, not enough
#     statistical information is presented to model these variations. Results for only an exemplar
#     neuron and entire population of recorded neurons.
# [3] Population level diagnostic data is misleading, it is flat, but should be incrementing
#     (at a rate faster than non-diagnostic data). This is an artifact of the way they tested.
#     Each individual diagnostic part was tested to show the animal could correctly decode the
#     identity of the object from it. Also it be be a result of the small stimulus set that they
#     used only 4 natural scene stimuli which the monkey may be  storing in working memory and
#     influencing the results of the IT neuron.
# [4] However for each occlusion level, higher firing rates were seen for diagnostic parts than
#     for non-diagnostic parts.
#
# Kovacs 1995:
# [5] Occlusion results at 3 different levels were presented, but for multiple objects.
#
# Oreilly 2013:
# [6] We also use results from Oreilly although we note that these are not actual recorded from
#     a monkey but simulated results.
#
# [7] We choose to optimize parameters of a sigmoid function to model occlusion responses.
#     At high occlusion levels, responses should be low as object identity is yet to be determined.
#     As more of the object is revealed stronger responses are anticipated and during the mid
#     level occlusion responses should rise sharply. At low occlusion rate of increase of
#     responses should plateau as the IT neuron will have some tolerance to small variations.

# load tuning curves
with open('Oreilly2013.pkl', 'rb') as fid:
    oreillyData = pickle.load(fid)

with open('Kovacs1995.pkl', 'rb') as fid:
    kovacsData = pickle.load(fid)

f, axArr = plt.subplots(3, 3, sharex='col', sharey='row')
f.subplots_adjust(hspace=0.05, wspace=0.05)
plt.suptitle('Sigmoid Fits to Non-diagnostic tuning curves 1/(1+exp(a*(x-b))) ', size=16)

x_arr = np.arange(start=1, stop=100, step=1)
pOptArray = np.array([])
pCovArray = np.array([])

# Curve Fits to non-diagnostic tuning profiles ------------------------------------------
# Fit Kovacs Data
for obj, perObjRates in enumerate(kovacsData['rates']):
    row = obj / 3
    col = obj - 3*row

    rMax = np.max(perObjRates)
    axArr[row][col].scatter(kovacsData['occlusion'], perObjRates / rMax)
    pOpt, pCov = curve_fit(sigmoid, kovacsData['occlusion'],
                           perObjRates / rMax)
    pOptArray = np.append(pOptArray, pOpt)
    pCovArray = np.append(pCovArray, pCov)

    legLabel = 'Kovacs 1995 Obj %i: a=%0.4f, b=%0.4f' % (obj, pOpt[0], pOpt[1])
    axArr[row][col].plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)

    axArr[row][col].legend(fontsize='small')
    axArr[row][col].set_xlim(0, 100)
    axArr[row][col].set_ylim(0, 1)

# Fit Oreilly Data
rMax = np.max(oreillyData['Rates'])
pOpt, pCov = curve_fit(sigmoid, oreillyData['Occ'],
                       oreillyData['Rates'] / rMax)

pOptArray = np.append(pOptArray, pOpt)
pCovArray = np.append(pCovArray, pCov)

axArr[1][2].scatter(oreillyData['Occ'], oreillyData['Rates'] / rMax)

legLabel = 'Oreilly 2013 a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
axArr[1][2].plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)
axArr[1][2].legend(fontsize='small')
axArr[1][2].set_xlim(0, 100)
axArr[1][2].set_ylim(0, 1)

axArr[2][0].set_xlabel('Occlusion Level')
axArr[2][1].set_xlabel('Occlusion Level')
axArr[2][2].set_xlabel('Occlusion Level')
axArr[0][0].set_ylabel('Normalized Firing Rate')
axArr[1][0].set_ylabel('Normalized Firing Rate')
axArr[2][0].set_ylabel('Normalized Firing Rate')

# Fit Neilson Data
rMax = np.max(data['singleNonDiagRate'])
pOpt, pCov = curve_fit(sigmoid, data['singleOcc'],
                       data['singleNonDiagRate'] / rMax, p0=[0.05, 30])

axArr[2][0].scatter(data['singleOcc'], data['singleNonDiagRate'] / rMax)
axArr[2][0].set_xlim(0, 100)
axArr[2][0].set_ylim(0, 1)

legLabel = 'Neilson 2006 Single Neuron a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
axArr[2][0].plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)
axArr[2][0].legend(fontsize='small')

pOptArray = np.append(pOptArray, pOpt)
pCovArray = np.append(pCovArray, pCov)

rMax = np.max(data['popNonDiagRate'])
pOpt, pCov = curve_fit(sigmoid, data['popOcc'],
                       data['popNonDiagRate'] / rMax, p0=[0.05, 30])

axArr[2][1].scatter(data['popOcc'], data['popNonDiagRate'] / rMax)
axArr[2][1].set_xlim(0, 100)
axArr[2][1].set_ylim(0, 1)

legLabel = 'Neilson 2006 Population a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
axArr[2][1].plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)
axArr[2][1].legend(fontsize='small')

# Curve fits for diagnostic profiles ----------------------------------------------------
# Single Neuron Data Fit to exemplar Neron in Neilson 2006.
plt.figure('Kovacs Data Fits')
rMax = np.max(data['singleDiagRate'])
pOpt, _ = curve_fit(sigmoid, data['singleOcc'],
                    data['singleDiagRate'] / rMax,
                    p0=[2, 100])

plt.scatter(data['singleOcc'], data['singleDiagRate'] / rMax)
legLabel = 'Neilson Single Neuron Diagnostic a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
plt.plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)

rMax = np.max(data['singleNonDiagRate'])
pOpt, _1 = curve_fit(sigmoid, data['singleOcc'],
                     data['singleNonDiagRate'] / rMax,
                     p0=[0.05, 30])

plt.scatter(data['singleOcc'], data['singleNonDiagRate'] / rMax)
legLabel = 'Neilson Exemplar Neuron NonDiagnostic a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
plt.plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)
plt.legend()

# Population Data
rMax = np.max(data['popDiagRate'])
pOpt, _2 = curve_fit(sigmoid, data['popOcc'],
                     data['popDiagRate'] / rMax,
                     p0=[2, 100])

plt.scatter(data['popOcc'], data['popDiagRate'] / rMax)
legLabel = 'Neilson Pop Neuron Diagnostic a=%0.4f, b=%0.4f' % (pOpt[0], pOpt[1])
plt.plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)

rMax = np.max(data['popNonDiagRate'])
pOpt, _3 = curve_fit(sigmoid, data['popOcc'],
                     data['popNonDiagRate'] / rMax,
                     p0=[0.05, 30])

plt.scatter(data['popOcc'], data['popNonDiagRate'] / rMax)
legLabel = 'Neilson Pop Neuron NonDiagnostic a=%0.4f, b=%0.4f' \
   % (pOpt[0], pOpt[1])
plt.plot(x_arr, sigmoid(x_arr, *pOpt), label=legLabel)
plt.legend()

# Average Parameters
pOptArray = np.reshape(pOptArray, (7, 2))

nonDiagAvgParams = np.mean(pOptArray, axis=0)
# nonDiagAvgParams = pOpt #Use Neilson population data
nonDiagAvgVar = np.mean(pOptArray, axis=0)

# Weighted Average Tuning Curve ---------------------------------------------------------
occ = np.arange(start=0, stop=100, step=1)

diagParams = np.array([0.32, 70])

plt.figure('Mean Tuning Curves')
plt.plot(occ,
         sigmoid(occ, diagParams[0], diagParams[1]),
         label='Diagnostic: a=%0.4f, b=%0.4f' % (diagParams[0], diagParams[1]))
plt.plot(occ,
         sigmoid(occ, nonDiagAvgParams[0], nonDiagAvgParams[1]),
         label='Non-Diagnostic: a=%0.4f, b=%0.4f' % (nonDiagAvgParams[0], nonDiagAvgParams[1]))

plt.legend()
plt.xlabel('Occlusion')
plt.ylabel('Normalized Firing Rate')
plt.title('Mean Model Neuron Occlusion Tuning Profiles, F(s) = 1/(1 + exp(a*(x-b)))')

diagVar = 60.0 / 100.0

occ1, occ2 = np.meshgrid(occ, occ)

fig = plt.figure()
ax = fig.gca(projection='3d')

Z = np.ones(shape=(100, 100))
for ii in np.arange(100):
    for jj in np.arange(100):
        Z[ii][jj] = diagVar * sigmoid(ii, *diagParams) + \
                    (1 - diagVar)*sigmoid(jj, *nonDiagAvgParams)

surf = ax.plot_surface(occ1, occ2, Z)
ax.set_xlabel('Occlusion - Diagnostic')
ax.set_ylabel('Occlusion - Non Diagnostic')
ax.set_zlabel('Normalized Firing Rate')
ax.set_title('Occlusion Tuning Profile of Sample Neuron with Diagnosticity of %f' % diagVar)
