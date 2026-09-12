'use client';

import { Suspense, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import * as THREE from 'three';

function AnomalyMotes({ count = 70 }: { count?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null!);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const data = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const speed = new Float32Array(count);
    const scale = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 6;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 6;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 3;
      speed[i] = 0.4 + Math.random() * 0.8;
      scale[i] = 0.03 + Math.random() * 0.05;
    }
    return { pos, speed, scale };
  }, [count]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.getElapsedTime();

    for (let i = 0; i < count; i++) {
      const y = data.pos[i * 3 + 1] + Math.sin(t * data.speed[i] + i) * 0.25;
      const x = data.pos[i * 3] + Math.cos(t * 0.3 * data.speed[i] + i) * 0.15;
      const z = data.pos[i * 3 + 2];

      dummy.position.set(x, y, z);
      const pulse = data.scale[i] * (1 + Math.sin(t * 2 + i) * 0.3);
      dummy.scale.set(pulse, pulse, pulse);
      dummy.updateMatrix();

      meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <octahedronGeometry args={[1, 0]} />
      <meshBasicMaterial color="#3CB697" transparent opacity={0.65} />
    </instancedMesh>
  );
}

function ForensicDocument() {
  const groupRef = useRef<THREE.Group>(null!);
  const scanLineRef = useRef<THREE.Mesh>(null!);
  const lightRef = useRef<THREE.PointLight>(null!);

  const width = 3.0;
  const height = 4.2;
  const depth = 0.04;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();

    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.4) * 0.15;
      groupRef.current.rotation.x = 0.1 + Math.cos(t * 0.3) * 0.08;
      groupRef.current.position.y = Math.sin(t * 0.6) * 0.1;
    }

    if (scanLineRef.current) {
      const scanY = Math.sin(t * 1.6) * (height * 0.46);
      scanLineRef.current.position.y = scanY;

      if (lightRef.current) {
        lightRef.current.position.y = scanY;
        lightRef.current.intensity = 1.5 + Math.sin(t * 8) * 0.3;
      }
    }
  });

  return (
    <group ref={groupRef} position={[0, 0.2, 0]}>
      <mesh>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color="#131620"
          roughness={0.2}
          metalness={0.6}
          transparent
          opacity={0.88}
        />
      </mesh>

      <mesh>
        <boxGeometry args={[width + 0.02, height + 0.02, depth + 0.01]} />
        <meshBasicMaterial color="#3CB697" wireframe transparent opacity={0.35} />
      </mesh>

      {[-1.4, -0.9, -0.4, 0.1, 0.6, 1.1, 1.6].map((y, idx) => (
        <group key={idx} position={[0, y, depth / 2 + 0.01]}>
          <mesh position={[-0.3, 0, 0]}>
            <planeGeometry args={[idx % 2 === 0 ? 1.8 : 2.2, 0.06]} />
            <meshBasicMaterial color="#8A90A4" transparent opacity={0.25} />
          </mesh>
          {idx === 2 && (
            <mesh position={[1.0, 0, 0]}>
              <planeGeometry args={[0.35, 0.06]} />
              <meshBasicMaterial color="#E05252" transparent opacity={0.7} />
            </mesh>
          )}
          {idx === 5 && (
            <mesh position={[0.9, 0, 0]}>
              <planeGeometry args={[0.4, 0.06]} />
              <meshBasicMaterial color="#3CB697" transparent opacity={0.7} />
            </mesh>
          )}
        </group>
      ))}

      <mesh ref={scanLineRef} position={[0, 0, depth / 2 + 0.03]}>
        <planeGeometry args={[width + 0.3, 0.06]} />
        <meshBasicMaterial color="#3CB697" transparent opacity={0.95} />
      </mesh>

      <pointLight
        ref={lightRef}
        color="#3CB697"
        distance={2.5}
        intensity={1.8}
        position={[0, 0, 0.3]}
      />
    </group>
  );
}

export default function HeroScene() {
  return (
    <div className="w-full h-full relative pointer-events-none select-none">
      <Canvas
        camera={{ position: [0, 0.5, 6.2], fov: 48 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} color="#E8E6DF" />
        <pointLight position={[-4, -2, 2]} intensity={0.8} color="#3CB697" />

        <Suspense fallback={null}>
          <ForensicDocument />
          <AnomalyMotes count={70} />

          <Grid
            position={[0, -2.6, 0]}
            args={[18, 18]}
            cellSize={0.5}
            cellThickness={0.8}
            cellColor="#3CB697"
            sectionSize={2.5}
            sectionThickness={1.2}
            sectionColor="#3CB697"
            fadeDistance={12}
            fadeStrength={1.6}
            infiniteGrid
          />

          <OrbitControls
            enableZoom={false}
            enablePan={false}
            enableRotate={false}
            autoRotate
            autoRotateSpeed={0.5}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
