"""Uniform lighting check: a matte sphere (albedo 0.5) lit only by the renderer's ambient light
(radiance 1) must have radiance 0.5 everywhere (white furnace test)."""
import os
import numpy as np
import pynari as anari

device = anari.newDevice('default')
sphere = device.newGeometry('sphere')
sphere.setParameter('vertex.position', anari.ARRAY1D,
                    device.newArray1D(anari.float3, np.array([0., 0., 0.], dtype=np.float32)))
sphere.setParameter('radius', anari.FLOAT32, 1.)
sphere.commitParameters()
material = device.newMaterial('matte')
material.setParameter('color', anari.float3, (0.5, 0.5, 0.5))
material.commitParameters()
surface = device.newSurface()
surface.setParameter('geometry', anari.GEOMETRY, sphere)
surface.setParameter('material', anari.MATERIAL, material)
surface.commitParameters()
world = device.newWorld()
world.setParameterArray1D('surface', anari.SURFACE, [surface])
world.commitParameters()

camera = device.newCamera('perspective')
camera.setParameter('aspect', anari.FLOAT32, 1.)
camera.setParameter('position', anari.float3, (0., 0., 4.))
camera.setParameter('direction', anari.float3, (0., 0., -1.))
camera.setParameter('up', anari.float3, (0., 1., 0.))
camera.setParameter('fovy', anari.FLOAT32, 0.6)
camera.commitParameters()

renderer = device.newRenderer(os.environ.get('RENDERER', 'default'))
renderer.setParameter('ambientRadiance', anari.FLOAT32, 1.)
renderer.setParameter('background', anari.float4, (0., 0., 0., 1.))
renderer.setParameter('pixelSamples', anari.INT32, 256)
renderer.commitParameters()

frame = device.newFrame()
frame.setParameter('size', anari.uint2, (64, 64))
frame.setParameter('channel.color', anari.DATA_TYPE, anari.FLOAT32_VEC4)
frame.setParameter('renderer', anari.RENDERER, renderer)
frame.setParameter('camera', anari.CAMERA, camera)
frame.setParameter('world', anari.WORLD, world)
frame.commitParameters()
frame.render()
pixels = np.array(frame.get('channel.color'))
center = pixels[24:40, 24:40, :3].mean()
print('RESULT sphere radiance {:.3f} (expected 0.5)'.format(center))
