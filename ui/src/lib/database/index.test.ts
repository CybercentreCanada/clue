import { v4 as uuid } from 'uuid';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import buildDatabase from './index';
import { ClueDatabase, SelectorDocType } from './types';

// Mock environment
vi.mock('lodash-es', () => ({
  throttle: vi.fn(fn => {
    const throttled = (...args: any[]) => fn(...args);
    throttled.cancel = vi.fn();
    throttled.flush = vi.fn();
    return throttled;
  })
}));

describe('Database', () => {
  let database: ClueDatabase;

  beforeAll(async () => {
    // Clear any existing storage
    vi.clearAllMocks();

    // Create a fresh database instance for each test
    database = await buildDatabase({ devMode: false, storageType: 'memory' });
  });

  afterAll(() => {
    if (database) {
      database.close();
    }
  });

  describe('Database Creation', () => {
    it('should create database with collections', async () => {
      expect(database).toBeDefined();
      expect(database.selectors).toBeDefined();
      expect(database.status).toBeDefined();
    });

    it('should have correct collection names', () => {
      expect(database.collections).toHaveProperty('selectors');
      expect(database.collections).toHaveProperty('status');
    });
  });

  describe('Selectors Collection', () => {
    const buildMock = () => ({
      id: uuid(),
      source: 'test-source',
      type: 'ip',
      value: '192.168.1.1',
      classification: 'TLP:WHITE',
      count: 5,
      link: 'https://example.com',
      raw_data: '{"test": "data"}',
      maintainer: 'test-maintainer',
      datahub_link: 'https://datahub.example.com',
      documentation_link: 'https://docs.example.com',
      latency: 100,
      annotations: [
        {
          confidence: 0,
          type: 'opinion' as const,
          value: 'benign',
          summary: '',
          quantity: 0,
          ubiquitous: false
        }
      ]
    });

    beforeEach(async () => {
      // For whatever reason, database.selectors.remove() hangs.
      await database.selectors.find({ selector: { id: { $exists: true } } }).remove();
    });

    it('should insert a selector document', async () => {
      const mockSelectorData = buildMock();

      const result = await database.selectors.insert(mockSelectorData);

      expect(result).toBeDefined();
      expect(result.id).toBe(mockSelectorData.id);
      expect(result.source).toBe(mockSelectorData.source);
      expect(result.type).toBe(mockSelectorData.type);
      expect(result.value).toBe(mockSelectorData.value);
    });

    it('should retrieve a selector document by id', async () => {
      const mockSelectorData = buildMock();

      await database.selectors.insert(mockSelectorData);

      const retrieved = await database.selectors.findOne(mockSelectorData.id).exec();

      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe(mockSelectorData.id);
      expect(retrieved?.source).toBe(mockSelectorData.source);
    });

    it('should update a selector document', async () => {
      const mockSelectorData = buildMock();

      const inserted = await database.selectors.insert(mockSelectorData);

      await inserted.update({
        $set: {
          count: 10
        }
      });

      const updated = await database.selectors.findOne(mockSelectorData.id).exec();
      expect(updated?.count).toBe(10);
    });

    it('should remove a selector document', async () => {
      const mockSelectorData = buildMock();

      await database.selectors.insert(mockSelectorData);

      const toRemove = await database.selectors.findOne(mockSelectorData.id).exec();
      await toRemove?.remove();

      const retrieved = await database.selectors.findOne(mockSelectorData.id).exec();
      expect(retrieved).toBeNull();
    });

    it('should find selectors by query', async () => {
      const mockSelectorData = buildMock();

      const selector1 = { ...mockSelectorData, id: 'selector-1', type: 'ip' };
      const selector2 = { ...mockSelectorData, id: 'selector-2', type: 'domain' };

      await database.selectors.insert(selector1);
      await database.selectors.insert(selector2);

      const ipSelectors = await database.selectors
        .find({
          selector: { type: 'ip' }
        })
        .exec();

      expect(ipSelectors).toHaveLength(1);
      expect(ipSelectors[0].type).toBe('ip');
    });

    it('should use getAnnotations method correctly', async () => {
      const mockSelectorData = buildMock();

      const inserted = await database.selectors.insert(mockSelectorData);

      const annotationsWithExtra = inserted.getAnnotations();

      expect(annotationsWithExtra).toHaveLength(1);
      expect(annotationsWithExtra[0]).toHaveProperty('type', 'opinion');
      expect(annotationsWithExtra[0]).toHaveProperty('value', 'benign');
      expect(annotationsWithExtra[0]).toHaveProperty('latency', 100);
      expect(annotationsWithExtra[0]).toHaveProperty('classification', 'TLP:WHITE');
    });

    it('should handle bulk insert', async () => {
      const mockSelectorData = buildMock();

      const bulkData = [
        { ...mockSelectorData, id: 'bulk-1' },
        { ...mockSelectorData, id: 'bulk-2' },
        { ...mockSelectorData, id: 'bulk-3' }
      ];

      const result = await database.selectors.bulkInsert(bulkData);

      expect(result.success).toHaveLength(3);
      expect(result.error).toHaveLength(0);
    });

    it('should handle duplicate key errors', async () => {
      const mockSelectorData = buildMock();

      await database.selectors.insert(mockSelectorData);

      const result = await database.selectors.bulkInsert([mockSelectorData]);

      expect(result.success).toHaveLength(0);
      expect(result.error).toHaveLength(1);
    });
  });

  describe('Status Collection', () => {
    const buildMock = () => ({
      id: uuid(),
      type: 'ip',
      value: '192.168.1.1',
      classification: 'TLP:WHITE',
      status: 'pending' as 'pending' | 'in-progress' | 'complete',
      sources: ['source1', 'source2']
    });

    beforeEach(async () => {
      // For whatever reason, database.status.remove() hangs.
      await database.status.find({ selector: { id: { $exists: true } } }).remove();
    });

    it('should insert a status document', async () => {
      const mockStatusData = buildMock();

      const result = await database.status.insert(mockStatusData);

      expect(result).toBeDefined();
      expect(result.id).toBe(mockStatusData.id);
      expect(result.type).toBe(mockStatusData.type);
      expect(result.status).toBe(mockStatusData.status);
    });

    it('should retrieve a status document by id', async () => {
      const mockStatusData = buildMock();
      await database.status.insert(mockStatusData);

      const retrieved = await database.status.findOne(mockStatusData.id).exec();

      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe(mockStatusData.id);
      expect(retrieved?.status).toBe(mockStatusData.status);
    });

    it('should update status document', async () => {
      const mockStatusData = buildMock();
      const inserted = await database.status.insert(mockStatusData);

      await inserted.update({
        $set: {
          status: 'in-progress'
        }
      });

      const updated = await database.status.findOne(mockStatusData.id).exec();
      expect(updated?.status).toBe('in-progress');
    });

    it('should remove a status document', async () => {
      const mockStatusData = buildMock();
      await database.status.insert(mockStatusData);

      const toRemove = await database.status.findOne(mockStatusData.id).exec();
      await toRemove?.remove();

      const retrieved = await database.status.findOne(mockStatusData.id).exec();
      expect(retrieved).toBeNull();
    });

    it('should use toSelector method correctly', async () => {
      const mockStatusData = buildMock();
      const inserted = await database.status.insert(mockStatusData);

      const selector = inserted.toSelector();

      expect(selector).toEqual({
        type: mockStatusData.type,
        value: mockStatusData.value,
        classification: mockStatusData.classification
      });
    });

    it('should find status by query', async () => {
      const complete = { ...buildMock(), id: 'status-2', status: 'complete' as const };

      await database.status.insert(complete);

      const pendingStatus = await database.status
        .find({
          selector: { status: 'complete' }
        })
        .exec();

      expect(pendingStatus).toHaveLength(1);
      expect(pendingStatus[0].status).toBe('complete');
    });

    it('should handle bulk insert', async () => {
      const mockStatusData = buildMock();
      const bulkData = [
        { ...mockStatusData, id: 'bulk-status-1' },
        { ...mockStatusData, id: 'bulk-status-2' },
        { ...mockStatusData, id: 'bulk-status-3' }
      ];

      const result = await database.status.bulkInsert(bulkData);

      expect(result.success).toHaveLength(3);
      expect(result.error).toHaveLength(0);
    });

    describe('queueInsert', () => {
      afterAll(() => {
        vi.useFakeTimers();
      });

      it('should handle one call', async () => {
        const mockStatusData = buildMock();
        const queuedStatus = { ...mockStatusData, id: 'queued-status-1' };

        const result = await database.status.queueInsert(queuedStatus);

        expect(result).toBeDefined();
        expect(result.id).toBe(queuedStatus.id);
      });

      it('should handle multiple calls', async () => {
        const mockStatusData = buildMock();
        const status1 = { ...mockStatusData, id: 'queued-1' };
        const status2 = { ...mockStatusData, id: 'queued-2' };

        const [result1, result2] = await Promise.all([
          database.status.queueInsert(status1),
          database.status.queueInsert(status2)
        ]);

        expect(result1.id).toBe('queued-1');
        expect(result2.id).toBe('queued-2');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid data insertion', async () => {
      const invalidData = {
        // Missing required fields
        id: 'invalid-1',
        // type is missing
        value: '192.168.1.1'
      } as SelectorDocType;

      await expect(database.selectors.insert(invalidData as any)).rejects.toThrow();
    });

    it('should handle query errors gracefully', async () => {
      // This test ensures the database handles malformed queries
      const results = await database.selectors
        .find({
          selector: { nonExistentField: 'value' } as any
        })
        .exec();

      expect(results).toHaveLength(0);
    });
  });
});
