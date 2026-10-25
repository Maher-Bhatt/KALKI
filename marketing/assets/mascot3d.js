/**
 * KALKI 3D Companion Mascot Engine
 * Real-Time Isometric & Perspective 3D Polygon Rendering on HTML5 Canvas
 * Zero External Dependencies • 60 FPS • Dynamic Filament Shading & Depth Sorting
 */

(function(global) {
  'use strict';

  // Math Helpers
  const DEG2RAD = Math.PI / 180;

  function rotateX(v, angle) {
    const c = Math.cos(angle), s = Math.sin(angle);
    return { x: v.x, y: v.y * c - v.z * s, z: v.y * s + v.z * c };
  }

  function rotateY(v, angle) {
    const c = Math.cos(angle), s = Math.sin(angle);
    return { x: v.x * c + v.z * s, y: v.y, z: -v.x * s + v.z * c };
  }

  function rotateZ(v, angle) {
    const c = Math.cos(angle), s = Math.sin(angle);
    return { x: v.x * c - v.y * s, y: v.x * s + v.y * c, z: v.z };
  }

  function transformVertex(v, rx, ry, rz, tx, ty, tz) {
    let p = rotateZ(v, rz);
    p = rotateX(p, rx);
    p = rotateY(p, ry);
    return { x: p.x + tx, y: p.y + ty, z: p.z + tz };
  }

  function crossProduct(a, b) {
    return {
      x: a.y * b.z - a.z * b.y,
      y: a.z * b.x - a.x * b.z,
      z: a.x * b.y - a.y * b.x
    };
  }

  function normalize(v) {
    const len = Math.hypot(v.x, v.y, v.z) || 1;
    return { x: v.x / len, y: v.y / len, z: v.z / len };
  }

  function dot(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
  }

  // Key light coming from top-right front
  const KEY_LIGHT = normalize({ x: 0.45, y: -0.75, z: 0.65 });

  // Color shading helper
  function shadeColor(hex, lum) {
    hex = String(hex).replace(/[^0-9a-f]/gi, '');
    if (hex.length < 6) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    lum = Math.max(0.12, Math.min(1.4, lum));
    let rgb = '#', c, i;
    for (i = 0; i < 3; i++) {
      c = parseInt(hex.substr(i*2, 2), 16);
      c = Math.round(Math.min(Math.max(0, c * lum), 255)).toString(16);
      rgb += ('00' + c).substr(c.length);
    }
    return rgb;
  }

  /* -------------------------------------------------------------
     3D Geometry Builders for the 6 Mascot Species
     ------------------------------------------------------------- */

  function makeBox(w, h, d, color, edgeColor = '#333b44') {
    const hw = w / 2, hh = h / 2, hd = d / 2;
    const verts = [
      { x: -hw, y: -hh, z: -hd }, { x:  hw, y: -hh, z: -hd },
      { x:  hw, y:  hh, z: -hd }, { x: -hw, y:  hh, z: -hd },
      { x: -hw, y: -hh, z:  hd }, { x:  hw, y: -hh, z:  hd },
      { x:  hw, y:  hh, z:  hd }, { x: -hw, y:  hh, z:  hd }
    ];
    const faces = [
      { indices: [0, 1, 2, 3], color, edgeColor }, // back
      { indices: [5, 4, 7, 6], color, edgeColor }, // front
      { indices: [4, 0, 3, 7], color, edgeColor }, // left
      { indices: [1, 5, 6, 2], color, edgeColor }, // right
      { indices: [4, 5, 1, 0], color, edgeColor }, // top
      { indices: [3, 2, 6, 7], color, edgeColor }  // bottom
    ];
    return { verts, faces };
  }

  function makeIcosahedron(radius, color, edgeColor = '#fff4e2') {
    const t = (1 + Math.sqrt(5)) / 2;
    const r = radius / Math.sqrt(1 + t * t);
    const verts = [
      { x: -r, y:  t*r, z: 0 }, { x:  r, y:  t*r, z: 0 }, { x: -r, y: -t*r, z: 0 }, { x:  r, y: -t*r, z: 0 },
      { x: 0, y: -r, z:  t*r }, { x: 0, y:  r, z:  t*r }, { x: 0, y: -r, z: -t*r }, { x: 0, y:  r, z: -t*r },
      { x:  t*r, y: 0, z: -r }, { x:  t*r, y: 0, z:  r }, { x: -t*r, y: 0, z: -r }, { x: -t*r, y: 0, z:  r }
    ];
    const triIndices = [
      [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
      [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
      [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
      [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
    ];
    const faces = triIndices.map(idx => ({ indices: idx, color, edgeColor }));
    return { verts, faces };
  }

  class Mascot3DEngine {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.options = Object.assign({
        species: 'gobi',
        scale: 1.0,
        fov: 340,
        isDancing: false,
        autoOrbit: true,
        showPlatform: true,
        interactive: true
      }, options);

      this.currentSpecies = this.options.species;
      this.isDancing = this.options.isDancing;
      this.tick = 0;
      this.animId = null;

      // Camera & Rotation State
      this.rotX = 0.14; // slight tilt down
      this.rotY = 0.0;
      this.rotZ = 0.0;
      this.targetRotX = 0.14;
      this.targetRotY = 0.0;

      // Mouse drag state
      this.isDragging = false;
      this.lastMouseX = 0;
      this.lastMouseY = 0;

      // Dynamic action states
      this.jumpY = 0;
      this.jumpVy = 0;
      this.happinessTimer = 0;
      this.particles = [];
      this.treats = [];

      this.initEvents();
      this.resize();
      this.start();
    }

    initEvents() {
      if (!this.options.interactive) return;

      const c = this.canvas;
      const getPos = (e) => {
        const rect = c.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
          x: clientX - rect.left,
          y: clientY - rect.top,
          normX: (clientX - rect.left - rect.width / 2) / (rect.width / 2),
          normY: (clientY - rect.top - rect.height / 2) / (rect.height / 2)
        };
      };

      c.addEventListener('mousedown', (e) => {
        this.isDragging = true;
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
      });

      window.addEventListener('mousemove', (e) => {
        if (this.isDragging) {
          const dx = e.clientX - this.lastMouseX;
          const dy = e.clientY - this.lastMouseY;
          this.targetRotY += dx * 0.012;
          this.targetRotX += dy * 0.012;
          this.targetRotX = Math.max(-0.6, Math.min(0.7, this.targetRotX));
          this.lastMouseX = e.clientX;
          this.lastMouseY = e.clientY;
        } else {
          // Look-at mouse tracking when hovering
          const rect = c.getBoundingClientRect();
          if (
            e.clientX >= rect.left && e.clientX <= rect.right &&
            e.clientY >= rect.top && e.clientY <= rect.bottom
          ) {
            const p = getPos(e);
            this.targetRotY = p.normX * 0.42;
            this.targetRotX = 0.14 + p.normY * 0.28;
          }
        }
      });

      window.addEventListener('mouseup', () => {
        this.isDragging = false;
      });

      c.addEventListener('click', () => {
        this.triggerJump();
      });
    }

    resize() {
      const dpr = window.devicePixelRatio || 1;
      const rect = this.canvas.getBoundingClientRect();
      const w = rect.width || this.canvas.width || 280;
      const h = rect.height || this.canvas.height || 280;
      this.canvas.width = w * dpr;
      this.canvas.height = h * dpr;
      this.ctx.scale(dpr, dpr);
      this.displayWidth = w;
      this.displayHeight = h;
    }

    setSpecies(name) {
      if (['gobi', 'kittu', 'byte', 'draco', 'nova', 'kitsu'].includes(name)) {
        this.currentSpecies = name;
        this.triggerMorph();
      }
    }

    setDancing(val) {
      this.isDancing = Boolean(val);
    }

    triggerJump() {
      if (this.jumpY === 0) {
        this.jumpVy = -9.0;
        this.happinessTimer = 45;
        this.addSparkles(0, -10, 16, '#fff4e2');
      }
    }

    triggerMorph() {
      this.targetRotY += Math.PI * 2;
      this.addSparkles(0, 0, 20, '#e08c33');
    }

    feedTreat(type = 'cookie') {
      const colors = {
        cookie: '#e08c33',
        fish: '#fff4e2',
        energy: '#4cc061',
        ember: '#ff5533',
        pearl: '#e8f4fc'
      };
      this.treats.push({
        x: (Math.random() - 0.5) * 30,
        y: -90,
        z: 20 + Math.random() * 20,
        vy: 2.0,
        rot: 0,
        color: colors[type] || '#fff4e2'
      });
      this.happinessTimer = 60;
    }

    addSparkles(x, y, count = 12, color = '#fff4e2') {
      for (let i = 0; i < count; i++) {
        this.particles.push({
          x: x + (Math.random() - 0.5) * 20,
          y: y + (Math.random() - 0.5) * 20,
          z: (Math.random() - 0.5) * 30,
          vx: (Math.random() - 0.5) * 3.5,
          vy: -Math.random() * 3.5 - 1.2,
          vz: (Math.random() - 0.5) * 3.5,
          life: 1.0,
          decay: 0.02 + Math.random() * 0.02,
          color: color,
          size: Math.random() * 2.8 + 1.6
        });
      }
    }

    start() {
      if (!this.animId) {
        const loop = () => {
          this.render();
          this.animId = requestAnimationFrame(loop);
        };
        this.animId = requestAnimationFrame(loop);
      }
    }

    stop() {
      if (this.animId) {
        cancelAnimationFrame(this.animId);
        this.animId = null;
      }
    }

    render() {
      this.tick++;
      const ctx = this.ctx;
      const w = this.displayWidth || 280;
      const h = this.displayHeight || 280;
      const cx = w / 2;
      const cy = h / 2 + 10;

      ctx.clearRect(0, 0, w, h);

      // Smooth camera interpolation
      if (!this.isDragging && this.options.autoOrbit) {
        this.rotY += 0.007; // gentle idle orbit
      }
      this.rotX += (this.targetRotX - this.rotX) * 0.08;
      this.rotY += (this.targetRotY - this.rotY) * 0.08;

      // Jump & Bounce Physics
      if (this.jumpVy !== 0 || this.jumpY !== 0) {
        this.jumpY += this.jumpVy;
        this.jumpVy += 0.52; // gravity
        if (this.jumpY >= 0) {
          this.jumpY = 0;
          this.jumpVy = 0;
        }
      }

      const danceBounce = this.isDancing ? Math.sin(this.tick * 0.16) * 12 : Math.sin(this.tick * 0.05) * 3.5;
      const danceRoll = this.isDancing ? Math.cos(this.tick * 0.16) * 0.08 : 0;
      const mascotY = this.jumpY + danceBounce;

      // 1. Draw 3D Platform (Holographic Wireframe Pedestal)
      if (this.options.showPlatform) {
        this.drawPlatform(ctx, cx, cy, this.rotX, this.rotY);
      }

      // 2. Gather 3D Polygons for Current Species
      const sceneFaces = this.buildSpeciesGeometry(this.currentSpecies, mascotY, danceRoll);

      // 3. Transform, Light, and Project
      const projectedFaces = [];
      const fov = this.options.fov;
      const scale = this.options.scale;

      for (const face of sceneFaces) {
        const worldVerts = [];
        let sumZ = 0;

        for (const v of face.verts) {
          const transformed = transformVertex(v, this.rotX, this.rotY, this.rotZ + danceRoll, 0, mascotY, 0);
          worldVerts.push(transformed);
          sumZ += transformed.z;
        }

        const avgZ = sumZ / worldVerts.length;
        const depth = avgZ + fov;
        if (depth <= 10) continue; // behind camera

        // Calculate face normal using first 3 vertices
        if (worldVerts.length >= 3) {
          const v0 = worldVerts[0], v1 = worldVerts[1], v2 = worldVerts[2];
          const edge1 = { x: v1.x - v0.x, y: v1.y - v0.y, z: v1.z - v0.z };
          const edge2 = { x: v2.x - v0.x, y: v2.y - v0.y, z: v2.z - v0.z };
          const normal = normalize(crossProduct(edge1, edge2));

          // Backface culling for solid meshes (unless doubleSided is true)
          if (!face.doubleSided && normal.z >= 0.05) {
            continue;
          }

          // Volumetric Diffuse Lighting
          const diffuse = Math.max(0, dot(normal, KEY_LIGHT));
          const lum = face.emissive ? 1.3 : 0.32 + diffuse * 0.78;
          const shadedColor = face.rawColor ? face.color : shadeColor(face.color, lum);

          // Project 3D -> 2D
          const screenPts = worldVerts.map(pt => {
            const f = fov / (pt.z + fov);
            return {
              x: cx + pt.x * scale * f,
              y: cy + pt.y * scale * f
            };
          });

          projectedFaces.push({
            pts: screenPts,
            avgZ: avgZ,
            fillColor: shadedColor,
            edgeColor: face.edgeColor || '#333b44',
            lineWidth: face.lineWidth || 1.1,
            emissive: face.emissive || false
          });
        }
      }

      // 4. Depth Sort (Painter's Algorithm: Furthest First)
      projectedFaces.sort((a, b) => a.avgZ - b.avgZ);

      // 5. Rasterize 3D Faces
      for (const f of projectedFaces) {
        ctx.beginPath();
        ctx.moveTo(f.pts[0].x, f.pts[0].y);
        for (let i = 1; i < f.pts.length; i++) {
          ctx.lineTo(f.pts[i].x, f.pts[i].y);
        }
        ctx.closePath();

        ctx.fillStyle = f.fillColor;
        ctx.fill();

        if (f.edgeColor) {
          ctx.strokeStyle = f.edgeColor;
          ctx.lineWidth = f.lineWidth;
          ctx.stroke();
        }

        // Emissive filament specular glint
        if (f.emissive) {
          ctx.save();
          ctx.shadowColor = 'rgba(255, 244, 226, 0.4)';
          ctx.shadowBlur = 8;
          ctx.stroke();
          ctx.restore();
        }
      }

      // 6. Update & Render Falling Treats
      this.updateTreats(ctx, cx, cy);

      // 7. Update & Render Sparkles/Embers
      this.updateParticles(ctx, cx, cy);
    }

    drawPlatform(ctx, cx, cy, rx, ry) {
      const platY = 68;
      const radius = 64;
      const rings = [radius, radius * 0.72, radius * 0.45];

      ctx.save();
      ctx.lineWidth = 1.0;

      // Rotating holographic radar rays
      const angleOffset = this.tick * 0.02;
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
        const rad = a + angleOffset;
        const x1 = Math.cos(rad) * radius;
        const z1 = Math.sin(rad) * radius;
        const p1 = this.projectPt({ x: x1, y: platY, z: z1 }, cx, cy, rx, ry);
        const p0 = this.projectPt({ x: 0, y: platY, z: 0 }, cx, cy, rx, ry);
        if (p0 && p1) {
          ctx.strokeStyle = 'rgba(51, 59, 68, 0.35)';
          ctx.beginPath();
          ctx.moveTo(p0.x, p0.y);
          ctx.lineTo(p1.x, p1.y);
          ctx.stroke();
        }
      }

      // Concentric rings
      for (let r of rings) {
        ctx.beginPath();
        let first = true;
        for (let i = 0; i <= 32; i++) {
          const theta = (i / 32) * Math.PI * 2;
          const x = Math.cos(theta) * r;
          const z = Math.sin(theta) * r;
          const p = this.projectPt({ x, y: platY, z }, cx, cy, rx, ry);
          if (p) {
            if (first) { ctx.moveTo(p.x, p.y); first = false; }
            else { ctx.lineTo(p.x, p.y); }
          }
        }
        ctx.strokeStyle = (r === radius) ? 'rgba(255, 244, 226, 0.3)' : 'rgba(76, 192, 97, 0.2)';
        ctx.stroke();
      }

      // Mascot Ground Shadow
      const shadowP = this.projectPt({ x: 0, y: platY - 1, z: 0 }, cx, cy, rx, ry);
      if (shadowP) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
        ctx.beginPath();
        ctx.ellipse(shadowP.x, shadowP.y, 40, 14, 0, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();
    }

    projectPt(v, cx, cy, rx, ry) {
      const p = transformVertex(v, rx, ry, 0, 0, 0, 0);
      const fov = this.options.fov;
      if (p.z + fov <= 10) return null;
      const f = fov / (p.z + fov);
      return {
        x: cx + p.x * this.options.scale * f,
        y: cy + p.y * this.options.scale * f
      };
    }

    updateTreats(ctx, cx, cy) {
      for (let i = this.treats.length - 1; i >= 0; i--) {
        const t = this.treats[i];
        t.y += t.vy;
        t.vy += 0.4;
        t.rot += 0.08;

        if (t.y >= 64) {
          t.y = 64;
          t.vy = -t.vy * 0.4;
          this.addSparkles(t.x, t.y, 6, t.color);
          if (Math.abs(t.vy) < 0.6) {
            this.treats.splice(i, 1);
            continue;
          }
        }

        const p = this.projectPt(t, cx, cy, this.rotX, this.rotY);
        if (p) {
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate(t.rot);
          ctx.fillStyle = t.color;
          ctx.shadowColor = t.color;
          ctx.shadowBlur = 6;
          ctx.fillRect(-6, -6, 12, 12);
          ctx.restore();
        }
      }
    }

    updateParticles(ctx, cx, cy) {
      for (let i = this.particles.length - 1; i >= 0; i--) {
        const p = this.particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;
        p.life -= p.decay;

        if (p.life <= 0) {
          this.particles.splice(i, 1);
          continue;
        }

        const pt = this.projectPt(p, cx, cy, this.rotX, this.rotY);
        if (pt) {
          ctx.save();
          ctx.globalAlpha = Math.max(0, p.life);
          ctx.fillStyle = p.color;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, p.size, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }
    }

    /* -------------------------------------------------------------
       Species Mesh Generators (Faceted Polyhedral 3D Solids)
       ------------------------------------------------------------- */
    buildSpeciesGeometry(species, mascotY, danceRoll) {
      const faces = [];
      const t = this.tick;

      if (species === 'gobi') {
        // GOBI: The Sentient AI Kitten
        // Head Cuboid (Machined Graphite)
        const head = makeBox(46, 40, 38, '#191d22', '#333b44');
        this.addMeshToFaces(faces, head, 0, -8, 0);

        // Triangular Ears (Filament Ivory + Amber Interior)
        const earTwitch = Math.sin(t * 0.08) * 4;
        const leftEar = {
          verts: [
            { x: -21, y: -28, z: -8 }, { x: -7, y: -28, z: 8 },
            { x: -26 + earTwitch, y: -52, z: 0 }
          ],
          color: '#fff4e2', edgeColor: '#e08c33', doubleSided: true
        };
        const rightEar = {
          verts: [
            { x: 21, y: -28, z: -8 }, { x: 7, y: -28, z: 8 },
            { x: 26 - earTwitch, y: -52, z: 0 }
          ],
          color: '#fff4e2', edgeColor: '#e08c33', doubleSided: true
        };
        faces.push(leftEar, rightEar);

        // Glowing Visor / Eyes
        const blink = Math.sin(t * 0.04) > 0.95;
        const eyeColor = blink ? '#333b44' : '#fff4e2';
        const leftEye = {
          verts: [
            { x: -16, y: -12, z: 20 }, { x: -6, y: -12, z: 20 },
            { x: -6, y: -4, z: 20 }, { x: -16, y: -4, z: 20 }
          ],
          color: eyeColor, edgeColor: '#fff4e2', emissive: !blink
        };
        const rightEye = {
          verts: [
            { x: 6, y: -12, z: 20 }, { x: 16, y: -12, z: 20 },
            { x: 16, y: -4, z: 20 }, { x: 6, y: -4, z: 20 }
          ],
          color: eyeColor, edgeColor: '#fff4e2', emissive: !blink
        };
        faces.push(leftEye, rightEye);

        // Amber Cheeks
        faces.push(
          { verts: [{x:-18, y:2, z:20}, {x:-12, y:2, z:20}, {x:-12, y:6, z:20}, {x:-18, y:6, z:20}], color: '#e08c33', edgeColor: null, emissive: true },
          { verts: [{x:12, y:2, z:20}, {x:18, y:2, z:20}, {x:18, y:6, z:20}, {x:12, y:6, z:20}], color: '#e08c33', edgeColor: null, emissive: true }
        );

        // Collar & Golden Emissive Bell
        const collar = makeBox(32, 6, 32, '#262c33', '#59636f');
        this.addMeshToFaces(faces, collar, 0, 16, 0);
        const bell = makeBox(8, 8, 8, '#fff4e2', '#ffd899');
        this.addMeshToFaces(faces, bell, 0, 20, 18);

        // Floating Paws
        const pawBob = Math.sin(t * 0.12) * 3;
        const leftPaw = makeBox(12, 10, 14, '#323941', '#59636f');
        this.addMeshToFaces(faces, leftPaw, -16, 28 + pawBob, 12);
        const rightPaw = makeBox(12, 10, 14, '#323941', '#59636f');
        this.addMeshToFaces(faces, rightPaw, 16, 28 - pawBob, 12);

        // 3D Wagging Tail (Segmented)
        const tailWag = Math.sin(t * 0.1) * 16;
        for (let seg = 0; seg < 3; seg++) {
          const tailBox = makeBox(6, 6, 8, '#262c33', '#333b44');
          this.addMeshToFaces(faces, tailBox, tailWag * (seg * 0.3), 10 - seg * 6, -18 - seg * 8);
        }

      } else if (species === 'kittu') {
        // KITTU: The Cyber Shiba Defender
        // Head
        const head = makeBox(44, 40, 36, '#262c33', '#333b44');
        this.addMeshToFaces(faces, head, 0, -8, 0);

        // Snout Muzzle
        const snout = makeBox(22, 16, 20, '#fff4e2', '#59636f');
        this.addMeshToFaces(faces, snout, 0, 2, 22);
        const nose = makeBox(6, 5, 4, '#070809', '#070809');
        this.addMeshToFaces(faces, nose, 0, -2, 33);

        // Sharp Shiba Ears
        faces.push(
          { verts: [{x:-20, y:-28, z:-4}, {x:-6, y:-28, z:6}, {x:-24, y:-54, z:2}], color: '#e08c33', edgeColor: '#fff4e2', doubleSided: true },
          { verts: [{x:20, y:-28, z:-4}, {x:6, y:-28, z:6}, {x:24, y:-54, z:2}], color: '#e08c33', edgeColor: '#fff4e2', doubleSided: true }
        );

        // ShieldCore Green Emblem Chestplate
        const chest = makeBox(28, 18, 12, '#191d22', '#4cc061');
        this.addMeshToFaces(faces, chest, 0, 20, 12);
        const emblem = makeBox(8, 8, 4, '#4cc061', '#4cc061');
        this.addMeshToFaces(faces, emblem, 0, 20, 19);

        // Curled Tail over back
        const wag = Math.sin(t * 0.18) * 8;
        for (let i = 0; i < 4; i++) {
          const seg = makeBox(7, 7, 7, '#e08c33', '#fff4e2');
          this.addMeshToFaces(faces, seg, wag * 0.3, 10 - i * 6, -18 + i * 4);
        }

      } else if (species === 'byte') {
        // BYTE: The Holographic Glitch Cube
        // Outer Wireframe Cage (Rotates on independent axis)
        const cageSize = 48;
        const cage = makeBox(cageSize, cageSize, cageSize, '#191d22', '#fff4e2');
        this.addMeshToFaces(faces, cage, 0, 0, 0);

        // Inner Glowing Voxel Core
        const core = makeBox(24, 24, 24, '#fff4e2', '#ffd899');
        this.addMeshToFaces(faces, core, 0, 0, 0);

        // Digital LED Eyes
        const eyeGlitch = (Math.sin(t * 0.2) > 0.8) ? 3 : 0;
        faces.push(
          { verts: [{x:-12, y:-6+eyeGlitch, z:26}, {x:-4, y:-6+eyeGlitch, z:26}, {x:-4, y:0+eyeGlitch, z:26}, {x:-12, y:0+eyeGlitch, z:26}], color: '#4cc061', edgeColor: null, emissive: true },
          { verts: [{x:4, y:-6-eyeGlitch, z:26}, {x:12, y:-6-eyeGlitch, z:26}, {x:12, y:0-eyeGlitch, z:26}, {x:4, y:0-eyeGlitch, z:26}], color: '#4cc061', edgeColor: null, emissive: true }
        );

        // Antenna with pulsing orb
        const antennaMast = makeBox(3, 20, 3, '#fff4e2', '#59636f');
        this.addMeshToFaces(faces, antennaMast, 0, -32, 0);
        const node = makeBox(8, 8, 8, '#fff4e2', '#fff4e2');
        this.addMeshToFaces(faces, node, 0, -44, 0);

        // 4 Orbiting Satellites
        for (let s = 0; s < 4; s++) {
          const orbAngle = t * 0.06 + (s * Math.PI / 2);
          const ox = Math.cos(orbAngle) * 38;
          const oz = Math.sin(orbAngle) * 38;
          const oy = Math.sin(t * 0.08 + s) * 12;
          const sat = makeBox(6, 6, 6, '#4cc061', '#fff4e2');
          this.addMeshToFaces(faces, sat, ox, oy, oz);
        }

      } else if (species === 'draco') {
        // DRACO: The Mini Cyber Dragon
        // Dragon Skull
        const head = makeBox(40, 36, 42, '#191d22', '#e08c33');
        this.addMeshToFaces(faces, head, 0, -6, 0);

        // Curved Swept Horns
        faces.push(
          { verts: [{x:-16, y:-24, z:-6}, {x:-6, y:-24, z:4}, {x:-32, y:-54, z:-18}], color: '#e08c33', edgeColor: '#ffd899', doubleSided: true },
          { verts: [{x:16, y:-24, z:-6}, {x:6, y:-24, z:4}, {x:32, y:-54, z:-18}], color: '#e08c33', edgeColor: '#ffd899', doubleSided: true }
        );

        // Slit Eyes
        faces.push(
          { verts: [{x:-14, y:-8, z:22}, {x:-6, y:-10, z:22}, {x:-8, y:-4, z:22}], color: '#e08c33', edgeColor: '#fff4e2', emissive: true },
          { verts: [{x:14, y:-8, z:22}, {x:6, y:-10, z:22}, {x:8, y:-4, z:22}], color: '#e08c33', edgeColor: '#fff4e2', emissive: true }
        );

        // Flapping 3D Wings
        const wingFlap = Math.sin(t * 0.16) * 22;
        faces.push(
          { verts: [{x:-18, y:4, z:-4}, {x:-58, y:-18 + wingFlap, z:-8}, {x:-46, y:22 + wingFlap, z:-12}], color: 'rgba(224, 140, 51, 0.85)', edgeColor: '#fff4e2', doubleSided: true },
          { verts: [{x:18, y:4, z:-4}, {x:58, y:-18 + wingFlap, z:-8}, {x:46, y:22 + wingFlap, z:-12}], color: 'rgba(224, 140, 51, 0.85)', edgeColor: '#fff4e2', doubleSided: true }
        );

        // Spiked Tail with Arrowhead Spade
        const tailSwish = Math.sin(t * 0.12) * 14;
        faces.push(
          { verts: [{x:tailSwish, y:18, z:-34}, {x:tailSwish - 8, y:24, z:-46}, {x:tailSwish + 8, y:24, z:-46}], color: '#e08c33', edgeColor: '#fff4e2', doubleSided: true }
        );

      } else if (species === 'nova') {
        // NOVA: The Astral Energy Polyhedron
        // 20-faced Geodesic Icosahedron
        const ico = makeIcosahedron(28, '#0d0f12', '#fff4e2');
        this.addMeshToFaces(faces, ico, 0, 0, 0);

        // Inner Radiant Octahedron
        const core = makeBox(14, 14, 14, '#fff4e2', '#ffd899');
        this.addMeshToFaces(faces, core, 0, 0, 0);

        // Gyroscopic Rings (Rotated in space)
        const rCount = 20;
        const ringRad = 42;
        for (let i = 0; i < rCount; i++) {
          const a1 = (i / rCount) * Math.PI * 2 + t * 0.03;
          const a2 = ((i + 1) / rCount) * Math.PI * 2 + t * 0.03;
          faces.push({
            verts: [
              { x: Math.cos(a1) * ringRad, y: Math.sin(a1) * ringRad, z: 0 },
              { x: Math.cos(a2) * ringRad, y: Math.sin(a2) * ringRad, z: 0 },
              { x: Math.cos(a2) * (ringRad - 2), y: Math.sin(a2) * (ringRad - 2), z: 0 }
            ],
            color: '#fff4e2', edgeColor: '#fff4e2', emissive: true, doubleSided: true
          });
        }

      } else if (species === 'kitsu') {
        // KITSU: Nine-Tailed Cyber Kitsune
        // Fox Mask Head
        const head = makeBox(42, 38, 36, '#fff4e2', '#333b44');
        this.addMeshToFaces(faces, head, 0, -8, 0);

        // Slanted Fox Eyes
        faces.push(
          { verts: [{x:-15, y:-6, z:19}, {x:-6, y:-8, z:19}, {x:-8, y:-2, z:19}], color: '#e08c33', edgeColor: null, emissive: true },
          { verts: [{x:15, y:-6, z:19}, {x:6, y:-8, z:19}, {x:8, y:-2, z:19}], color: '#e08c33', edgeColor: null, emissive: true }
        );

        // Forehead Red Diamond Crest
        faces.push({
          verts: [{x:0, y:-18, z:19}, {x:4, y:-14, z:19}, {x:0, y:-10, z:19}, {x:-4, y:-14, z:19}],
          color: '#e08c33', edgeColor: '#ffd899', emissive: true
        });

        // 9 Harmonic Fan Tails
        const tailCount = 9;
        for (let k = 0; k < tailCount; k++) {
          const spreadAngle = ((k - 4) / 4) * 0.85; // fan from -0.85 rad to +0.85 rad
          const wavePhase = t * 0.12 - k * 0.38;
          const waveAmp = Math.sin(wavePhase) * 14;

          const baseX = Math.sin(spreadAngle) * 18;
          const tipX = Math.sin(spreadAngle) * 48 + waveAmp;
          const tipY = -28 + Math.abs(k - 4) * 6;
          const tipZ = -36 - Math.cos(spreadAngle) * 14;

          faces.push({
            verts: [
              { x: baseX - 3, y: 16, z: -18 },
              { x: baseX + 3, y: 16, z: -18 },
              { x: tipX, y: tipY, z: tipZ }
            ],
            color: (k % 2 === 0) ? '#e08c33' : '#fff4e2',
            edgeColor: '#333b44',
            doubleSided: true
          });
        }
      }

      return faces;
    }

    addMeshToFaces(destFaces, mesh, ox, oy, oz) {
      for (const f of mesh.faces) {
        const faceVerts = f.indices.map(i => {
          const v = mesh.verts[i];
          return { x: v.x + ox, y: v.y + oy, z: v.z + oz };
        });
        destFaces.push({
          verts: faceVerts,
          color: f.color,
          edgeColor: f.edgeColor,
          emissive: f.emissive || false
        });
      }
    }
  }

  // Export to global scope
  global.Mascot3DEngine = Mascot3DEngine;

})(typeof window !== 'undefined' ? window : this);
