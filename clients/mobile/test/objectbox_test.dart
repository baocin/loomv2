import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import '../lib/models/objectbox/entities.dart';

// Define Note class for testing since it may not be defined in the entities.dart directly
class Note {
  int id = 0;
  String title;
  String content;
  int userId;
  DateTime created;
  DateTime modified;

  Note({
    required this.title,
    required this.content,
    required this.userId,
    required this.created,
    required this.modified,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'userId': userId,
      'created': created.toIso8601String(),
      'modified': modified.toIso8601String(),
    };
  }
}

// Extend User class for testing to add embedding property
class TestUser extends User {
  Uint8List? embedding;

  TestUser({required String username}) : super(username: username);
}

// Create mock classes
class MockStore extends Mock {}

class MockBox<T> extends Mock {
  List<T> items = [];

  int put(T item) {
    if (item is User) {
      final user = item as User;
      if (user.id == 0) {
        user.id = items.length + 1;
      }
      items.add(item);
      return user.id;
    } else if (item is Device) {
      final device = item as Device;
      if (device.id == 0) {
        device.id = items.length + 1;
      }
      items.add(item);
      return device.id;
    } else if (item is Node) {
      final node = item as Node;
      if (node.id == 0) {
        node.id = items.length + 1;
      }
      items.add(item);
      return node.id;
    } else if (item is Edge) {
      final edge = item as Edge;
      if (edge.id == 0) {
        edge.id = items.length + 1;
      }
      items.add(item);
      return edge.id;
    } else if (item is Note) {
      final note = item as Note;
      if (note.id == 0) {
        note.id = items.length + 1;
      }
      items.add(item);
      return note.id;
    }
    return 0;
  }

  T? get(int id) {
    try {
      return items.firstWhere((item) {
        if (item is User) return (item as User).id == id;
        if (item is Device) return (item as Device).id == id;
        if (item is Node) return (item as Node).id == id;
        if (item is Edge) return (item as Edge).id == id;
        if (item is Note) return (item as Note).id == id;
        return false;
      });
    } catch (_) {
      return null;
    }
  }

  List<T> getAll() {
    return items;
  }

  bool remove(int id) {
    final initialSize = items.length;
    items.removeWhere((item) {
      if (item is User) return (item as User).id == id;
      if (item is Device) return (item as Device).id == id;
      if (item is Node) return (item as Node).id == id;
      if (item is Edge) return (item as Edge).id == id;
      if (item is Note) return (item as Note).id == id;
      return false;
    });
    return initialSize != items.length;
  }

  MockQuery<T> query() {
    return MockQuery<T>(items);
  }
}

class MockQuery<T> extends Mock {
  final List<T> items;

  MockQuery(this.items);

  MockQuery<T> build() {
    return this;
  }

  List<T> find() {
    return items;
  }

  MockQuery<T> filter(bool Function(T) predicate) {
    return MockQuery<T>(items.where(predicate).toList());
  }
}

// Mock repository for testing
class MockObjectBoxRepository {
  final MockBox<TestUser> _userBox = MockBox<TestUser>();
  final MockBox<Device> _deviceBox = MockBox<Device>();
  final MockBox<Node> _nodeBox = MockBox<Node>();
  final MockBox<Edge> _edgeBox = MockBox<Edge>();
  final MockBox<Note> _noteBox = MockBox<Note>();

  // Return all users
  List<TestUser> getUsers() {
    return _userBox.getAll();
  }

  // Get a specific user
  TestUser? getUser(int id) {
    return _userBox.get(id);
  }

  // Insert a user
  Future<int> insertUser(String username) async {
    final user = TestUser(username: username);
    return _userBox.put(user);
  }

  // Return all devices
  List<Device> getDevices() {
    return _deviceBox.getAll();
  }

  // Get a specific device
  Device? getDevice(int id) {
    return _deviceBox.get(id);
  }

  // Get devices by user
  List<Device> getDevicesByUserId(int userId) {
    return _deviceBox.getAll().where((d) => d.userId == userId).toList();
  }

  // Insert a device
  Future<int> insertDevice(
      String deviceName, int userId, String affordances) async {
    final device = Device(
      deviceName: deviceName,
      userId: userId,
      affordances: affordances,
    );
    return _deviceBox.put(device);
  }

  // Insert a data node
  Future<int> insertDataNode(int layer, DateTime timestamp, int deviceId,
      int userId, String dataType, String data) async {
    final node = Node(
      layer: layer,
      timestamp: timestamp,
      deviceId: deviceId,
      userId: userId,
      type: dataType,
      data: data,
      embeddingVector: null,
    );
    return _nodeBox.put(node);
  }

  // Insert an edge
  Future<int> insertEdge(int fromId, int toId, String relationshipType) async {
    final edge = Edge(
      fromId: fromId,
      toId: toId,
      relationshipType: relationshipType,
    );
    return _edgeBox.put(edge);
  }

  // Delete a node
  Future<bool> deleteNode(int nodeId) async {
    return _nodeBox.remove(nodeId);
  }

  // Get nodes by user
  List<Node> getNodesByUserId(int userId) {
    return _nodeBox.getAll().where((n) => n.userId == userId).toList();
  }

  // Get nodes by type
  List<Node> getNodesByType(String type) {
    return _nodeBox.getAll().where((node) => node.type == type).toList();
  }

  // Get edges from a node
  List<Edge> getEdgesFromNode(int nodeId) {
    return _edgeBox.getAll().where((edge) => edge.fromId == nodeId).toList();
  }

  // Get edges to a node
  List<Edge> getEdgesToNode(int nodeId) {
    return _edgeBox.getAll().where((edge) => edge.toId == nodeId).toList();
  }

  // Note operations
  Future<int> insertNote(String title, String content, int userId) async {
    final note = Note(
      title: title,
      content: content,
      userId: userId,
      created: DateTime.now(),
      modified: DateTime.now(),
    );
    return _noteBox.put(note);
  }

  Note? getNote(int id) {
    return _noteBox.get(id);
  }

  List<Note> getNotesByUserId(int userId) {
    return _noteBox.getAll().where((n) => n.userId == userId).toList();
  }

  Future<bool> deleteNote(int id) async {
    return _noteBox.remove(id);
  }

  // Update a user with vector embedding (simulated)
  Future<bool> updateUserEmbedding(int userId, Uint8List embedding) async {
    final user = _userBox.get(userId);
    if (user != null) {
      user.embedding = embedding;
      _userBox.put(user);
      return true;
    }
    return false;
  }
}

void main() {
  late MockObjectBoxRepository repository;

  setUp(() {
    repository = MockObjectBoxRepository();
  });

  group('User operations', () {
    test('Insert and retrieve a user', () async {
      // Create a test user
      final username = 'TestUser';
      final userId = await repository.insertUser(username);

      // Verify user ID is valid
      expect(userId, greaterThan(0));

      // Verify user can be retrieved
      final users = repository.getUsers();
      expect(users, isNotEmpty);
      expect(users.first.username, equals(username));
    });

    test('Get user by ID', () async {
      final userId = await repository.insertUser('TestUser');
      final user = repository.getUser(userId);

      expect(user, isNotNull);
      expect(user?.username, equals('TestUser'));
    });
  });

  group('Device operations', () {
    test('Insert and retrieve a device', () async {
      // Create a test user first
      final userId = await repository.insertUser('TestUser');

      // Create a test device
      final deviceName = 'TestDevice';
      final affordances = jsonEncode({
        'affordances': ['test', 'record_audio'],
        'identifier': 'test-device',
      });

      final deviceId =
          await repository.insertDevice(deviceName, userId, affordances);

      // Verify device ID is valid
      expect(deviceId, greaterThan(0));

      // Verify device can be retrieved
      final devices = repository.getDevices();
      expect(devices, isNotEmpty);
      expect(devices.first.deviceName, equals(deviceName));
      expect(devices.first.userId, equals(userId));
    });

    test('Get devices by user ID', () async {
      final userId1 = await repository.insertUser('User1');
      final userId2 = await repository.insertUser('User2');

      await repository.insertDevice('Device1', userId1, '{}');
      await repository.insertDevice('Device2', userId1, '{}');
      await repository.insertDevice('Device3', userId2, '{}');

      final user1Devices = repository.getDevicesByUserId(userId1);
      final user2Devices = repository.getDevicesByUserId(userId2);

      expect(user1Devices.length, equals(2));
      expect(user2Devices.length, equals(1));
    });
  });

  group('Data node operations', () {
    test('Insert and retrieve a data node', () async {
      // Create a test user and device first
      final userId = await repository.insertUser('TestUser');
      final deviceId =
          await repository.insertDevice('TestDevice', userId, '{}');

      // Create a test data node
      final data = jsonEncode({
        'test': true,
        'content': 'Test content',
      });

      final nodeId = await repository.insertDataNode(
        0, // Raw data layer
        DateTime.now(),
        deviceId,
        userId,
        'TestData',
        data,
      );

      // Verify node ID is valid
      expect(nodeId, greaterThan(0));

      // Verify node can be retrieved
      final nodes = repository.getNodesByType('TestData');
      expect(nodes, isNotEmpty);
      expect(nodes.first.type, equals('TestData'));
      expect(nodes.first.userId, equals(userId));
      expect(nodes.first.deviceId, equals(deviceId));

      // Verify node data
      final parsedData = nodes.first.parsedData;
      expect(parsedData['test'], isTrue);
      expect(parsedData['content'], equals('Test content'));
    });

    test('Get nodes by user ID', () async {
      final userId1 = await repository.insertUser('User1');
      final userId2 = await repository.insertUser('User2');
      final deviceId =
          await repository.insertDevice('TestDevice', userId1, '{}');

      await repository.insertDataNode(
          0, DateTime.now(), deviceId, userId1, 'Type1', '{}');
      await repository.insertDataNode(
          0, DateTime.now(), deviceId, userId1, 'Type2', '{}');
      await repository.insertDataNode(
          0, DateTime.now(), deviceId, userId2, 'Type1', '{}');

      final user1Nodes = repository.getNodesByUserId(userId1);
      final user2Nodes = repository.getNodesByUserId(userId2);

      expect(user1Nodes.length, equals(2));
      expect(user2Nodes.length, equals(1));
    });
  });

  group('Edge operations', () {
    test('Create and update relationships between nodes', () async {
      // Create a test user and device first
      final userId = await repository.insertUser('TestUser');
      final deviceId =
          await repository.insertDevice('TestDevice', userId, '{}');

      // Create two test nodes
      final sourceNodeId = await repository.insertDataNode(
        0, // Raw data layer
        DateTime.now(),
        deviceId,
        userId,
        'SourceNode',
        '{"source": true}',
      );

      final targetNodeId = await repository.insertDataNode(
        1, // Processed layer
        DateTime.now(),
        deviceId,
        userId,
        'TargetNode',
        '{"target": true}',
      );

      // Create a relationship
      final edgeId = await repository.insertEdge(
        sourceNodeId,
        targetNodeId,
        'derived_from',
      );

      // Verify edge ID is valid
      expect(edgeId, greaterThan(0));

      // Verify edges can be retrieved
      final outgoingEdges = repository.getEdgesFromNode(sourceNodeId);
      expect(outgoingEdges, isNotEmpty);
      expect(outgoingEdges.first.fromId, equals(sourceNodeId));
      expect(outgoingEdges.first.toId, equals(targetNodeId));
      expect(outgoingEdges.first.relationshipType, equals('derived_from'));

      final incomingEdges = repository.getEdgesToNode(targetNodeId);
      expect(incomingEdges, isNotEmpty);
      expect(incomingEdges.first.fromId, equals(sourceNodeId));
      expect(incomingEdges.first.toId, equals(targetNodeId));
    });
  });

  group('Delete operations', () {
    test('Delete a node', () async {
      // Create a test user and device first
      final userId = await repository.insertUser('TestUser');
      final deviceId =
          await repository.insertDevice('TestDevice', userId, '{}');

      // Create a test node
      final nodeId = await repository.insertDataNode(
        0,
        DateTime.now(),
        deviceId,
        userId,
        'TestNode',
        '{}',
      );

      // Verify node exists
      var nodes = repository.getNodesByType('TestNode');
      expect(nodes, isNotEmpty);

      // Delete the node
      final deleted = await repository.deleteNode(nodeId);
      expect(deleted, isTrue);

      // Verify node no longer exists
      nodes = repository.getNodesByType('TestNode');
      expect(nodes, isEmpty);
    });
  });

  group('Note operations', () {
    test('Insert and retrieve notes', () async {
      final userId = await repository.insertUser('TestUser');

      final noteId = await repository.insertNote(
          'Test Note', 'This is a test note content', userId);

      expect(noteId, greaterThan(0));

      final retrievedNote = repository.getNote(noteId);
      expect(retrievedNote, isNotNull);
      expect(retrievedNote?.title, equals('Test Note'));
      expect(retrievedNote?.content, equals('This is a test note content'));
      expect(retrievedNote?.userId, equals(userId));
    });

    test('Get notes by user ID', () async {
      final userId1 = await repository.insertUser('User1');
      final userId2 = await repository.insertUser('User2');

      await repository.insertNote('Note 1', 'Content 1', userId1);
      await repository.insertNote('Note 2', 'Content 2', userId1);
      await repository.insertNote('Note 3', 'Content 3', userId2);

      final user1Notes = repository.getNotesByUserId(userId1);
      final user2Notes = repository.getNotesByUserId(userId2);

      expect(user1Notes.length, equals(2));
      expect(user2Notes.length, equals(1));
    });

    test('Delete a note', () async {
      final userId = await repository.insertUser('TestUser');
      final noteId =
          await repository.insertNote('Test Note', 'Content', userId);

      final notes = repository.getNotesByUserId(userId);
      expect(notes.length, equals(1));

      final deleted = await repository.deleteNote(noteId);
      expect(deleted, isTrue);

      final notesAfterDelete = repository.getNotesByUserId(userId);
      expect(notesAfterDelete, isEmpty);
    });
  });

  group('Vector operations', () {
    test('Update and retrieve user embedding', () async {
      final userId = await repository.insertUser('TestUser');

      // Create a simple test vector
      final testVector = Uint8List.fromList([1, 2, 3, 4, 5, 6, 7, 8]);

      // Update the user's embedding
      final updated = await repository.updateUserEmbedding(userId, testVector);
      expect(updated, isTrue);

      // Retrieve the user and check the embedding
      final user = repository.getUser(userId);
      expect(user?.embedding, isNotNull);
      expect(user?.embedding, equals(testVector));
    });
  });
}
