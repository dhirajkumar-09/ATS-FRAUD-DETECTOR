'use client';

import { Suspense, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, MeshDistortMaterial, Stars } from '@react-three/drei';
import * as THREE from 'three';

// ── Floating particles ─────────────────────────────────────────────────────
function Particles({ count = 80 }: { count?: number }) {
  const mesh = useRef<THREE.InstancedMesh>(null!);
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/rules-of-hooks
      // Actually it's react-hooks/purity for the custom rule or we can just suppress all
      // eslint-disable-next-line
      pos[i * 3] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 10;
    }
    return pos;
  }, [count]);

  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    for (let i = 0; i < count; i++) {
      dummy.position.set(
        positions[i * 3] + Math.sin(t * 0.3 + i) * 0.1,
        positions[i * 3 + 1] + Math.cos(t * 0.2 + i) * 0.1,
        positions[i * 3 + 2],
      );
      dummy.scale.setScalar(0.03 + Math.sin(t + i) * 0.01);
      dummy.updateMatrix();
      mesh.current.setMatrixAt(i, dummy.matrix);
    }
    mesh.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#3CB697" />
    </instancedMesh>
  );
}

// ── Central distorted sphere (shield) ─────────────────────────────────────
function Shield() {
  const meshRef = useRef<THREE.Mesh>(null!);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    meshRef.current.rotation.y = t * 0.15;
    meshRef.current.rotation.x = Math.sin(t * 0.1) * 0.1;
  });

  return (
    <mesh ref={meshRef}>
      <Sphere args={[1.4, 32, 32]}>
        <MeshDistortMaterial
          color="#3CB697"
          attach="material"
          distort={0.35}
          speed={1.5}
          roughness={0.1}
          metalness={0.8}
          transparent
          opacity={0.18}
          wireframe={false}
        />
      </Sphere>
    </mesh>
  );
}

// ── Wireframe octahedron ──────────────────────────────────────────────────
function Octahedron() {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    ref.current.rotation.y = t * 0.3;
    ref.current.rotation.z = t * 0.1;
  });

  return (
    <mesh ref={ref}>
      <octahedronGeometry args={[1.8, 0]} />
      <meshBasicMaterial color="#3CB697" wireframe transparent opacity={0.12} />
    </mesh>
  );
}

// ── Orbit rings ───────────────────────────────────────────────────────────
function OrbitRing({ radius, speed, tilt }: { radius: number; speed: number; tilt: number }) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    ref.current.rotation.z = t * speed;
    ref.current.rotation.x = tilt;
  });

  return (
    <mesh ref={ref}>
      <torusGeometry args={[radius, 0.008, 16, 120]} />
      <meshBasicMaterial color="#3CB697" transparent opacity={0.25} />
    </mesh>
  );
}

// ── Scene canvas ──────────────────────────────────────────────────────────
export default function AuthScene() {
  return (
    <div className="w-full h-full" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 60 }}
        dpr={[1, 1.5]}
        performance={{ min: 0.5 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1.5} color="#3CB697" />
        <pointLight position={[-5, -5, -3]} intensity={0.5} color="#6B8CFF" />

        <Suspense fallback={null}>
          <Stars radius={40} depth={30} count={800} factor={3} fade speed={0.5} />
          <Shield />
          <Octahedron />
          <OrbitRing radius={2.4} speed={0.4} tilt={Math.PI / 4} />
          <OrbitRing radius={2.8} speed={-0.25} tilt={-Math.PI / 5} />
          <OrbitRing radius={3.2} speed={0.15} tilt={Math.PI / 8} />
          <Particles count={60} />
        </Suspense>

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.5}
          minPolarAngle={Math.PI / 3}
          maxPolarAngle={Math.PI / 1.8}
        />
      </Canvas>
    </div>
  );
}
