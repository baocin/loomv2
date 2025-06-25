export class MemoryCache<T> {
  private cache: Map<string, { data: T; timestamp: number }> = new Map()
  private ttl: number

  constructor(ttlMs: number = 30000) {
    this.ttl = ttlMs
  }

  set(key: string, data: T): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    })
  }

  get(key: string): T | null {
    const entry = this.cache.get(key)

    if (!entry) {
      return null
    }

    // Check if expired
    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key)
      return null
    }

    return entry.data
  }

  has(key: string): boolean {
    return this.get(key) !== null
  }

  delete(key: string): boolean {
    return this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }

  size(): number {
    // Clean expired entries first
    this.cleanExpired()
    return this.cache.size
  }

  keys(): string[] {
    this.cleanExpired()
    return Array.from(this.cache.keys())
  }

  private cleanExpired(): void {
    const now = Date.now()

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.ttl) {
        this.cache.delete(key)
      }
    }
  }
}
