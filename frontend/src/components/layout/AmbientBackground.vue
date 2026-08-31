<template>
  <canvas ref="canvas" class="pointer-events-none fixed inset-0 -z-10 h-full w-full" />
</template>

<script>
// Named imports (not `import * as THREE`) so Rollup can tree-shake the rest of three.js —
// this file uses a handful of classes, not the whole library.
import { BufferAttribute, BufferGeometry, PerspectiveCamera, Points, PointsMaterial, Scene, WebGLRenderer } from "three"
import { markRaw } from "vue"

// A quiet, low-poly particle drift behind the app shell — purely ambient, never competing with
// data. Kept cheap on purpose: ~180 points, no postprocessing, paused when the tab is hidden or
// the viewer has prefers-reduced-motion set, so it never costs GPU nobody is looking at.
const PARTICLE_COUNT = 180

export default {
  name: "AmbientBackground",
  data() {
    return {
      renderer: null,
      scene: null,
      camera: null,
      points: null,
      frameId: null,
      resizeObserver: null,
    }
  },
  mounted() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
    // Deferred a frame: reading viewport size synchronously in mounted() raced layout in some
    // startup orderings and produced a 0x0 canvas — requestAnimationFrame guarantees a completed
    // layout pass first.
    requestAnimationFrame(this.init)
  },
  beforeUnmount() {
    if (this.frameId) cancelAnimationFrame(this.frameId)
    this.resizeObserver?.disconnect()
    this.renderer?.dispose()
  },
  methods: {
    getViewportSize() {
      return { width: document.documentElement.clientWidth || window.innerWidth, height: document.documentElement.clientHeight || window.innerHeight }
    },
    init() {
      const canvas = this.$refs.canvas
      const { width, height } = this.getViewportSize()
      if (!width || !height) {
        requestAnimationFrame(this.init)
        return
      }

      // markRaw: without it, Vue's data() reactivity deep-wraps these three.js objects in
      // Proxies, and three.js's internal identity checks (e.g. matrixWorld comparisons during
      // render) fail against a Proxy that isn't strictly === the real instance.
      this.scene = markRaw(new Scene())
      this.camera = markRaw(new PerspectiveCamera(55, width / height, 0.1, 100))
      this.camera.position.z = 18

      this.renderer = markRaw(new WebGLRenderer({ canvas, alpha: true, antialias: true }))
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
      this.renderer.setSize(width, height)

      const positions = new Float32Array(PARTICLE_COUNT * 3)
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 40
        positions[i * 3 + 1] = (Math.random() - 0.5) * 24
        positions[i * 3 + 2] = (Math.random() - 0.5) * 20
      }
      const geometry = new BufferGeometry()
      geometry.setAttribute("position", new BufferAttribute(positions, 3))

      const isDark = document.documentElement.getAttribute("data-theme") === "dark"
      const material = new PointsMaterial({
        color: isDark ? 0xffffff : 0x0a0a0c,
        size: 0.06,
        transparent: true,
        opacity: isDark ? 0.4 : 0.22,
        sizeAttenuation: true,
      })

      this.points = markRaw(new Points(geometry, material))
      this.scene.add(this.points)

      this.resizeObserver = new ResizeObserver(() => this.handleResize())
      this.resizeObserver.observe(document.body)

      this.animate()
    },
    animate() {
      if (document.hidden) {
        this.frameId = requestAnimationFrame(this.animate)
        return
      }
      this.points.rotation.y += 0.0004
      this.points.rotation.x += 0.0001
      this.renderer.render(this.scene, this.camera)
      this.frameId = requestAnimationFrame(this.animate)
    },
    handleResize() {
      const { width, height } = this.getViewportSize()
      if (!width || !height) return
      this.camera.aspect = width / height
      this.camera.updateProjectionMatrix()
      this.renderer.setSize(width, height)
    },
  },
}
</script>
