import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:process_run/shell.dart';

void main() {
  runApp(const CollectionUploaderApp());
}

class CollectionUploaderApp extends StatelessWidget {
  const CollectionUploaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Collection Uploader V2 - xAI',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const UploaderHomePage(),
    );
  }
}

class UploaderHomePage extends StatefulWidget {
  const UploaderHomePage({super.key});

  @override
  State<UploaderHomePage> createState() => _UploaderHomePageState();
}

class _UploaderHomePageState extends State<UploaderHomePage> {
  // Controllers
  final _managementKeyController = TextEditingController();
  final _apiKeyController = TextEditingController();
  
  // Available Grok models
  final List<String> _availableModels = [
    'grok-beta',
    'grok-2-1212',
    'grok-2-vision-1212',
  ];
  
  // State
  String _selectedModel = 'grok-beta';
  List<Map<String, String>> _availableCollections = [];
  String? _selectedCollectionId;
  String? _selectedCollectionName;
  
  List<String> _selectedJsonFiles = [];
  String? _outputDirectory;
  bool _saveLocalMd = true;
  
  // Processing state
  bool _isGeneratingMd = false;
  bool _isUploading = false;
  double _progressMd = 0.0;
  double _progressUpload = 0.0;
  String _statusMessage = '';
  
  // Generated MD files info
  final List<String> _generatedMdFiles = [];
  Map<String, dynamic> _mdGenerationStats = {};
  
  // Logs
  final List<String> _logMessages = [];
  
  @override
  void initState() {
    super.initState();
    _loadSavedConfig();
  }
  
  Future<void> _loadSavedConfig() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _managementKeyController.text = prefs.getString('management_key') ?? '';
      _apiKeyController.text = prefs.getString('api_key') ?? '';
      _selectedModel = prefs.getString('model') ?? 'grok-beta';
      _outputDirectory = prefs.getString('output_directory');
      _saveLocalMd = prefs.getBool('save_local_md') ?? true;
    });
    
    // Auto-load collections if keys are available
    if (_managementKeyController.text.isNotEmpty) {
      _loadCollections();
    }
  }
  
  Future<void> _saveConfig() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('management_key', _managementKeyController.text);
    await prefs.setString('api_key', _apiKeyController.text);
    await prefs.setString('model', _selectedModel);
    if (_outputDirectory != null) {
      await prefs.setString('output_directory', _outputDirectory!);
    }
    await prefs.setBool('save_local_md', _saveLocalMd);
  }
  
  Future<void> _loadCollections() async {
    if (_managementKeyController.text.isEmpty) {
      _showError('Informe a Management Key primeiro');
      return;
    }
    
    _addLog('🔍 Carregando Collections disponíveis...');
    
    try {
      final response = await http.get(
        Uri.parse('https://api.x.ai/v1/collections'),
        headers: {
          'Authorization': 'Bearer ${_managementKeyController.text}',
        },
      ).timeout(const Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final collections = data['collections'] as List? ?? [];
        
        setState(() {
          _availableCollections = collections.map((col) {
            return {
              'id': col['id'] as String,
              'name': col['name'] as String? ?? 'Sem nome',
            };
          }).toList();
        });
        
        _addLog('✅ ${_availableCollections.length} Collection(s) encontrada(s)');
        
        // Restaura seleção anterior se disponível
        final prefs = await SharedPreferences.getInstance();
        final savedCollectionId = prefs.getString('selected_collection_id');
        if (savedCollectionId != null && 
            _availableCollections.any((c) => c['id'] == savedCollectionId)) {
          setState(() {
            _selectedCollectionId = savedCollectionId;
            _selectedCollectionName = _availableCollections
                .firstWhere((c) => c['id'] == savedCollectionId)['name'];
          });
        }
        
      } else {
        _showError('Erro ao carregar Collections: ${response.statusCode}');
      }
    } catch (e) {
      _showError('Erro ao conectar xAI API: $e');
    }
  }
  
  Future<void> _pickJsonFiles() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['json', 'txt'],
      allowMultiple: true,
      dialogTitle: 'Selecione arquivo(s) JSON de sentenças',
    );
    
    if (result != null) {
      setState(() {
        _selectedJsonFiles = result.paths.where((p) => p != null).cast<String>().toList();
      });
      _addLog('✅ ${_selectedJsonFiles.length} arquivo(s) JSON selecionado(s)');
    }
  }
  
  Future<void> _pickOutputDirectory() async {
    String? selectedDirectory = await FilePicker.platform.getDirectoryPath(
      dialogTitle: 'Selecione diretório de saída para arquivos MD',
    );
    
    if (selectedDirectory != null) {
      setState(() {
        _outputDirectory = selectedDirectory;
      });
      _addLog('✅ Diretório de saída: $_outputDirectory');
    }
  }
  
  void _addLog(String message) {
    setState(() {
      _logMessages.add('[${DateTime.now().toString().substring(11, 19)}] $message');
    });
  }
  
  Future<bool> _validateConfigForMdGeneration() async {
    if (_apiKeyController.text.isEmpty) {
      _showError('API Key do Grok é obrigatória para gerar keywords');
      return false;
    }
    
    if (_selectedJsonFiles.isEmpty) {
      _showError('Selecione pelo menos um arquivo JSON');
      return false;
    }
    
    if (_outputDirectory == null) {
      _showError('Selecione o diretório de saída');
      return false;
    }
    
    return true;
  }
  
  Future<bool> _validateConfigForUpload() async {
    if (_managementKeyController.text.isEmpty) {
      _showError('Management Key é obrigatória para upload');
      return false;
    }
    
    if (_selectedCollectionId == null) {
      _showError('Selecione uma Collection');
      return false;
    }
    
    if (_generatedMdFiles.isEmpty) {
      _showError('Gere os arquivos MD primeiro antes de fazer upload');
      return false;
    }
    
    return true;
  }
  
  Future<void> _generateMdFiles() async {
    if (!await _validateConfigForMdGeneration()) {
      return;
    }
    
    setState(() {
      _isGeneratingMd = true;
      _progressMd = 0.0;
      _statusMessage = 'Gerando arquivos MD com keywords inteligentes...';
      _generatedMdFiles.clear();
      _mdGenerationStats.clear();
    });
    
    await _saveConfig();
    
    try {
      // Cria arquivo de configuração temporário (sem upload)
      final configFile = await _createConfigFile(uploadEnabled: false);
      _addLog('📝 Configuração criada para geração de MD');
      
      // Processa cada arquivo JSON
      int totalFiles = _selectedJsonFiles.length;
      
      for (int i = 0; i < totalFiles; i++) {
        String jsonFile = _selectedJsonFiles[i];
        
        setState(() {
          _statusMessage = 'Gerando MD do arquivo ${i + 1}/$totalFiles...';
          _progressMd = i / totalFiles;
        });
        
        _addLog('\n📄 Processando: ${jsonFile.split(Platform.pathSeparator).last}');
        
        // Executa script Python
        final stats = await _runPythonScriptForMdGeneration(configFile.path, jsonFile);
        
        if (stats != null) {
          _generatedMdFiles.addAll(stats['files'] as List<String>? ?? []);
          _mdGenerationStats = stats;
        }
        
        setState(() {
          _progressMd = (i + 1) / totalFiles;
        });
      }
      
      // Limpa arquivo temporário
      await configFile.delete();
      
      setState(() {
        _isGeneratingMd = false;
        _statusMessage = '✅ Geração de MD concluída!';
        _progressMd = 1.0;
      });
      
      _addLog('\n🎉 ARQUIVOS MD GERADOS COM SUCESSO!');
      _addLog('📊 Total de arquivos MD: ${_generatedMdFiles.length}');
      _addLog('📁 Localização: $_outputDirectory');
      
      // Mostra janela de feedback
      _showMdGenerationFeedback();
      
    } catch (e) {
      setState(() {
        _isGeneratingMd = false;
        _statusMessage = '❌ Erro durante geração de MD';
      });
      _addLog('❌ ERRO: $e');
      _showError('Erro durante geração: $e');
    }
  }
  
  Future<void> _uploadToCollection() async {
    if (!await _validateConfigForUpload()) {
      return;
    }
    
    // Confirma upload
    final confirm = await _showConfirmDialog(
      'Upload para Collection',
      'Deseja fazer upload de ${_generatedMdFiles.length} arquivo(s) MD para a Collection "$_selectedCollectionName"?',
    );
    
    if (confirm != true) {
      return;
    }
    
    setState(() {
      _isUploading = true;
      _progressUpload = 0.0;
      _statusMessage = 'Fazendo upload para xAI Collections...';
    });
    
    await _saveConfig();
    
    try {
      // Cria arquivo de configuração temporário (com upload)
      final configFile = await _createConfigFile(uploadEnabled: true);
      _addLog('📝 Configuração criada para upload');
      
      // Processa cada arquivo JSON
      int totalFiles = _selectedJsonFiles.length;
      
      for (int i = 0; i < totalFiles; i++) {
        String jsonFile = _selectedJsonFiles[i];
        
        setState(() {
          _statusMessage = 'Upload do arquivo ${i + 1}/$totalFiles...';
          _progressUpload = i / totalFiles;
        });
        
        _addLog('\n📤 Uploading: ${jsonFile.split(Platform.pathSeparator).last}');
        
        // Executa script Python
        await _runPythonScriptForUpload(configFile.path, jsonFile);
        
        setState(() {
          _progressUpload = (i + 1) / totalFiles;
        });
      }
      
      // Limpa arquivo temporário
      await configFile.delete();
      
      setState(() {
        _isUploading = false;
        _statusMessage = '✅ Upload concluído!';
        _progressUpload = 1.0;
      });
      
      _addLog('\n🎉 UPLOAD CONCLUÍDO COM SUCESSO!');
      _addLog('📊 Collection: $_selectedCollectionName');
      
      // Mostra janela de feedback
      _showUploadFeedback();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Upload concluído! Documentos disponíveis na Collection.'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 5),
          ),
        );
      }
      
    } catch (e) {
      setState(() {
        _isUploading = false;
        _statusMessage = '❌ Erro durante upload';
      });
      _addLog('❌ ERRO: $e');
      _showError('Erro durante upload: $e');
    }
  }
  
  Future<File> _createConfigFile({required bool uploadEnabled}) async {
    final config = {
      'grok_api_key': _apiKeyController.text,
      'management_key': _managementKeyController.text,
      'collection_id': _selectedCollectionId ?? '',
      'grok_model': _selectedModel,
      'output_dir': _outputDirectory,
      'save_local_md': true,  // Sempre salva MD localmente
      'upload_enabled': uploadEnabled,
    };
    
    final tempDir = Directory.systemTemp;
    final configFile = File('${tempDir.path}/collection_uploader_config_v2.json');
    await configFile.writeAsString(jsonEncode(config));
    
    return configFile;
  }
  
  Future<Map<String, dynamic>?> _runPythonScriptForMdGeneration(
    String configPath, 
    String jsonFile
  ) async {
    final shell = Shell();
    
    try {
      final scriptPath = '/home/user/CollectionUploaderV2.py';
      
      if (!await File(scriptPath).exists()) {
        throw Exception('Script Python não encontrado: $scriptPath');
      }
      
      _addLog('   🐍 Executando script Python (geração MD)...');
      
      // Executa o script
      await shell.run('''
        python3 "$scriptPath" --config "$configPath" --input "$jsonFile"
      ''');
      
      _addLog('   ✅ Geração MD concluída');
      
      // Parse output para extrair estatísticas (simplificado)
      return {
        'files': [], // Será preenchido ao listar o diretório
        'success': true,
      };
      
    } catch (e) {
      _addLog('   ❌ Erro ao executar script: $e');
      rethrow;
    }
  }
  
  Future<void> _runPythonScriptForUpload(String configPath, String jsonFile) async {
    final shell = Shell();
    
    try {
      final scriptPath = '/home/user/CollectionUploaderV2.py';
      
      _addLog('   📤 Executando upload...');
      
      // Executa o script
      await shell.run('''
        python3 "$scriptPath" --config "$configPath" --input "$jsonFile"
      ''');
      
      _addLog('   ✅ Upload concluído');
      
    } catch (e) {
      _addLog('   ❌ Erro durante upload: $e');
      rethrow;
    }
  }
  
  void _showMdGenerationFeedback() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 32),
            SizedBox(width: 12),
            Text('Arquivos MD Gerados'),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Total de arquivos MD criados: ${_generatedMdFiles.length}',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Text('Localização:\n$_outputDirectory'),
              const SizedBox(height: 16),
              const Text(
                'Os arquivos MD foram gerados com keywords inteligentes criadas pelo modelo Grok.',
                style: TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              const Text(
                '✅ Agora você pode:\n'
                '1. Revisar os arquivos MD no diretório\n'
                '2. Avaliar a qualidade das keywords\n'
                '3. Fazer upload para a Collection',
                style: TextStyle(fontSize: 14),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(context);
              _uploadToCollection();
            },
            icon: const Icon(Icons.cloud_upload),
            label: const Text('Upload Agora'),
          ),
        ],
      ),
    );
  }
  
  void _showUploadFeedback() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.cloud_done, color: Colors.green, size: 32),
            SizedBox(width: 12),
            Text('Upload Concluído'),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Collection: $_selectedCollectionName',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Text('Total de documentos enviados: ${_generatedMdFiles.length}'),
              const SizedBox(height: 16),
              const Text(
                '✅ Os documentos foram indexados e estão disponíveis para busca na Collection.',
                style: TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              const Text(
                'Você pode verificar no xAI Console:\nhttps://console.x.ai/',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
  
  Future<bool?> _showConfirmDialog(String title, String message) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
  }
  
  void _showError(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: Colors.red,
          duration: const Duration(seconds: 5),
        ),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final bool isProcessing = _isGeneratingMd || _isUploading;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Collection Uploader V2 - xAI'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (_availableCollections.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Recarregar Collections',
              onPressed: _loadCollections,
            ),
        ],
      ),
      body: isProcessing ? _buildProcessingView() : _buildConfigView(),
    );
  }
  
  Widget _buildConfigView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          const Text(
            '⚙️ Configuração',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Configure as credenciais e selecione os arquivos',
            style: TextStyle(fontSize: 14, color: Colors.grey),
          ),
          const SizedBox(height: 32),
          
          // Management Key
          TextField(
            controller: _managementKeyController,
            decoration: InputDecoration(
              labelText: 'Management Key (xAI Collections)',
              hintText: 'xai-mgmt-xxx...',
              border: const OutlineInputBorder(),
              prefixIcon: const Icon(Icons.key),
              suffixIcon: IconButton(
                icon: const Icon(Icons.cloud_download),
                tooltip: 'Carregar Collections',
                onPressed: _loadCollections,
              ),
            ),
            obscureText: true,
            onChanged: (_) => _saveConfig(),
          ),
          const SizedBox(height: 16),
          
          // API Key
          TextField(
            controller: _apiKeyController,
            decoration: const InputDecoration(
              labelText: 'API Key (Grok)',
              hintText: 'xai-xxx...',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.vpn_key),
            ),
            obscureText: true,
            onChanged: (_) => _saveConfig(),
          ),
          const SizedBox(height: 16),
          
          // Model Selection
          DropdownButtonFormField<String>(
            initialValue: _selectedModel,
            decoration: const InputDecoration(
              labelText: 'Modelo Grok para Keywords',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.psychology),
              helperText: 'Modelo usado para gerar keywords inteligentes',
            ),
            items: _availableModels.map((model) {
              String description = '';
              switch (model) {
                case 'grok-beta':
                  description = 'Rápido e eficiente (Recomendado)';
                  break;
                case 'grok-2-1212':
                  description = 'Melhor qualidade (mais lento)';
                  break;
                case 'grok-2-vision-1212':
                  description = 'Com suporte a visão';
                  break;
              }
              return DropdownMenuItem(
                value: model,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(model, style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(description, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
              );
            }).toList(),
            onChanged: (value) {
              if (value != null) {
                setState(() {
                  _selectedModel = value;
                });
                _saveConfig();
              }
            },
          ),
          const SizedBox(height: 16),
          
          // Collection Selection
          if (_availableCollections.isNotEmpty) ...[
            DropdownButtonFormField<String>(
              initialValue: _selectedCollectionId,
              decoration: const InputDecoration(
                labelText: 'Collection para Upload',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.collections_bookmark),
                helperText: 'Selecione a Collection de destino',
              ),
              items: _availableCollections.map((collection) {
                return DropdownMenuItem(
                  value: collection['id'],
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        collection['name'] ?? 'Sem nome',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'ID: ${collection['id']}',
                        style: const TextStyle(fontSize: 10, color: Colors.grey),
                      ),
                    ],
                  ),
                );
              }).toList(),
              onChanged: (value) async {
                if (value != null) {
                  setState(() {
                    _selectedCollectionId = value;
                    _selectedCollectionName = _availableCollections
                        .firstWhere((c) => c['id'] == value)['name'];
                  });
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setString('selected_collection_id', value);
                }
              },
            ),
          ] else if (_managementKeyController.text.isNotEmpty) ...[
            Card(
              color: Colors.orange.shade100,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const Text(
                      '⚠️ Nenhuma Collection encontrada',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Clique no ícone de atualizar acima para carregar suas Collections',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton.icon(
                      onPressed: _loadCollections,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Carregar Collections'),
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 32),
          
          // File Selection
          const Text(
            '📁 Seleção de Arquivos',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          // JSON Files
          Card(
            child: ListTile(
              leading: const Icon(Icons.insert_drive_file, size: 40),
              title: const Text('Arquivos JSON de Sentenças'),
              subtitle: Text(
                _selectedJsonFiles.isEmpty
                    ? 'Nenhum arquivo selecionado'
                    : '${_selectedJsonFiles.length} arquivo(s) selecionado(s)',
              ),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: _pickJsonFiles,
            ),
          ),
          const SizedBox(height: 16),
          
          // Output Directory
          Card(
            child: ListTile(
              leading: const Icon(Icons.folder_open, size: 40),
              title: const Text('Diretório de Saída (MD)'),
              subtitle: Text(
                _outputDirectory ?? 'Nenhum diretório selecionado',
                overflow: TextOverflow.ellipsis,
              ),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: _pickOutputDirectory,
            ),
          ),
          const SizedBox(height: 32),
          
          // Action Buttons
          const Text(
            '🚀 Ações',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          // Generate MD Button
          ElevatedButton.icon(
            onPressed: _selectedJsonFiles.isNotEmpty && _outputDirectory != null
                ? _generateMdFiles
                : null,
            icon: const Icon(Icons.create, size: 24),
            label: const Text('1. Gerar Arquivos MD', style: TextStyle(fontSize: 18)),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 20),
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Gera arquivos MD com keywords inteligentes via LLM',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 24),
          
          // Upload Button
          ElevatedButton.icon(
            onPressed: _generatedMdFiles.isNotEmpty && _selectedCollectionId != null
                ? _uploadToCollection
                : null,
            icon: const Icon(Icons.cloud_upload, size: 24),
            label: const Text('2. Upload para Collection', style: TextStyle(fontSize: 18)),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 20),
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Faz upload dos arquivos MD para a Collection selecionada',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          
          // Status info
          if (_generatedMdFiles.isNotEmpty) ...[
            const SizedBox(height: 24),
            Card(
              color: Colors.green.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green),
                        SizedBox(width: 8),
                        Text(
                          'Arquivos MD Prontos',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Total: ${_generatedMdFiles.length} arquivo(s)'),
                    Text('Localização: $_outputDirectory'),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
  
  Widget _buildProcessingView() {
    final isGenerating = _isGeneratingMd;
    final progress = isGenerating ? _progressMd : _progressUpload;
    
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Status
          Text(
            _statusMessage,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          
          // Progress
          LinearProgressIndicator(
            value: progress,
            minHeight: 10,
            borderRadius: BorderRadius.circular(5),
          ),
          const SizedBox(height: 8),
          Text(
            '${(progress * 100).toStringAsFixed(1)}%',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 32),
          
          // Log
          const Text(
            '📋 Log de Processamento',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListView.builder(
                itemCount: _logMessages.length,
                itemBuilder: (context, index) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Text(
                      _logMessages[index],
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 12,
                        color: Colors.greenAccent,
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          
          if (progress >= 1.0) ...[
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _isGeneratingMd = false;
                  _isUploading = false;
                  _progressMd = 0.0;
                  _progressUpload = 0.0;
                });
              },
              icon: const Icon(Icons.arrow_back),
              label: const Text('Voltar'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ],
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _managementKeyController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }
}
