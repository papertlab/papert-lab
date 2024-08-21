
const getTextColor = (role) => {
    switch (role) {
        case 'assistant':
            return 'text-yellow-400';
        case 'user':
            return 'text-green-400';
        case 'system':
            return 'text-blue-400';
        default:
            return 'text-gray-300';
    }
};

const MessageContent = ({ content, role }) => {
    const codeBlockRegex = /(<<<<<<< SEARCH\n([\s\S]*?)>>>>>>> REPLACE)|(```(\w*)\n([\s\S]*?)```)/g;
    const [parts, setParts] = React.useState([]);
    const codeMirrorInstances = React.useRef({});

    React.useEffect(() => {
        const newParts = [];
        let lastIndex = 0;
        let match;

        while ((match = codeBlockRegex.exec(content)) !== null) {
            if (match.index > lastIndex) {
                newParts.push({ type: 'text', content: content.slice(lastIndex, match.index) });
            }
            if (match[1]) {
                // This is a <<<<< SEARCH ... >>>>> REPLACE block
                newParts.push({ type: 'code', content: match[2].trim(), id: `code-${newParts.length}`, language: 'javascript' });
            } else {
                // This is a ```...``` block
                newParts.push({ 
                    type: 'code', 
                    content: match[5].trim(), 
                    id: `code-${newParts.length}`, 
                    language: match[4] || 'javascript'
                });
            }
            lastIndex = match.index + match[0].length;
        }

        if (lastIndex < content.length) {
            newParts.push({ type: 'text', content: content.slice(lastIndex) });
        }

        setParts(newParts);
    }, [content]);

    React.useEffect(() => {
        parts.forEach(part => {
            if (part.type === 'code') {
                const element = document.getElementById(part.id);
                if (element && !codeMirrorInstances.current[part.id]) {
                    const lineCount = part.content.split('\n').length;
                    const editorHeight = Math.min(lineCount * 20, 400); // 20px per line, max 400px

                    codeMirrorInstances.current[part.id] = CodeMirror(element, {
                        value: part.content,
                        mode: 'javascript',
                        theme: 'default',
                        readOnly: true,
                        lineNumbers: true,
                        viewportMargin: Infinity,
                        height: `${editorHeight}px`
                    });
                } else if (codeMirrorInstances.current[part.id]) {
                    const instance = codeMirrorInstances.current[part.id];
                    instance.setValue(part.content);
                    
                    const lineCount = instance.lineCount();
                    const editorHeight = Math.min(lineCount * 20, 400);
                    instance.setSize(null, `${editorHeight}px`);
                    
                    instance.refresh();
                }
            }
        });

        return () => {
            Object.keys(codeMirrorInstances.current).forEach(id => {
                if (!parts.some(part => part.id === id)) {
                    codeMirrorInstances.current[id].toTextArea();
                    delete codeMirrorInstances.current[id];
                }
            });
        };
    }, [parts]);

    return (
        <span>
            {parts.map((part, index) => {
                if (part.type === 'code') {
                    return (
                        <div key={part.id} className="my-2 overflow-hidden rounded border border-gray-600">
                            <div id={part.id} className="bg-white"></div>
                        </div>
                    );
                } else {
                    return (
                        <span key={index} className={getTextColor(role)}>
                            {part.content}
                        </span>
                    );
                }
            })}
        </span>
    );
};


const App = () => {
    const [messages, setMessages] = React.useState([]);
    const [input, setInput] = React.useState('');
    const [files, setFiles] = React.useState({});
    const [showApiKeyModal, setShowApiKeyModal] = React.useState(false);
    const [apiKey, setApiKey] = React.useState('');
    const [anthropicApiKey, setAnthropicApiKey] = React.useState('');
    const [monthlyTokenUsage, setMonthlyTokenUsage] = React.useState(0);
    const [monthlyCost, setMonthlyCost] = React.useState(0);
    const [showFilePanel, setShowFilePanel] = React.useState(false);
    const [selectedModel, setSelectedModel] = React.useState(null);
    const [models, setModels] = React.useState([]);
    const [selectedFile, setSelectedFile] = React.useState(null);
    const [fileContent, setFileContent] = React.useState('');
    const [selectedFiles, setSelectedFiles] = React.useState({});
    const [logs, setLogs] = React.useState([]);
    const [isInitializing, setIsInitializing] = React.useState(true);
    const [fullPaths, setFullPaths] = React.useState({});
    const [selectedCommand, setSelectedCommand] = React.useState('code');
    const [showCommandDropdown, setShowCommandDropdown] = React.useState(false);
    const messagesEndRef = React.useRef(null);
    const editorRef = React.useRef(null);
    const codeMirrorInstanceRef = React.useRef(null);
    const dropdownRef = React.useRef(null);
    const [unsupportedFile, setUnsupportedFile] = React.useState(null);

    const handleCommandSelect = (command) => {
        setSelectedCommand(command);
        setShowCommandDropdown(false);
    };

    React.useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setShowCommandDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);


    const autoSave = async () => {
        if (selectedFile && codeMirrorInstanceRef.current) {
            try {
                const content = codeMirrorInstanceRef.current.getValue();
                const response = await fetch('/api/update_file', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file: selectedFile,
                        content: content,
                    }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                console.log(data.message);
            } catch (error) {
                console.error('Error saving file:', error);
            }
        }
    };

    const checkInitializationStatus = React.useCallback(async () => {
        try {
            const response = await fetch('/api/initialization_status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.complete) {
                setIsInitializing(false);
                setFiles(data.files || {});
                setModels(data.models || []);
                setSelectedModel(data.current_model || null);
                if (Array.isArray(data.announcements)) {
                    setMessages(data.announcements.map(announcement => ({ role: 'system', content: announcement })));
                }
            } else {
                setTimeout(checkInitializationStatus, 2000); // Check again in 2 seconds
            }
        } catch (error) {
            console.error('Error checking initialization status:', error);
            setTimeout(checkInitializationStatus, 5000); // Retry in 5 seconds if there's an error
        }
    }, []);

    React.useEffect(() => {
        const initializeApp = async () => {
            try {
                await fetch('/api/init', { method: 'POST' });
                checkInitializationStatus();
            } catch (error) {
                console.error('Error starting initialization:', error);
                setIsInitializing(false);
            }
        };

        initializeApp();
    }, [checkInitializationStatus]);

    const fetchMonthlyUsage = React.useCallback(async () => {
        try {
            const response = await fetch('/api/monthly_usage');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setMonthlyTokenUsage(data.total_tokens || 0);
            setMonthlyCost(data.total_cost || 0);
        } catch (error) {
            console.error('Error fetching monthly usage:', error);
            setMonthlyTokenUsage(0);
            setMonthlyCost(0);
        }
    }, []);

    React.useEffect(() => {
        fetchMonthlyUsage();
        const intervalId = setInterval(fetchMonthlyUsage, 5 * 60 * 1000);
        return () => clearInterval(intervalId);
    }, [fetchMonthlyUsage]);

    const getFullPath = React.useCallback((structure, path = '') => {
        if (!structure || typeof structure !== 'object') {
            return {};
        }
        const result = {};
        Object.entries(structure).forEach(([key, value]) => {
            const newPath = path ? `${path}/${key}` : key;
            if (typeof value === 'string') {
                result[key] = value;
            } else {
                Object.assign(result, getFullPath(value, newPath));
            }
        });
        return result;
    }, []);

    React.useEffect(() => {
        if (files && typeof files === 'object') {
            setFullPaths(getFullPath(files));
        }
    }, [files, getFullPath]);

    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    React.useEffect(() => {
        if (selectedFile && editorRef.current) {
            if (typeof CodeMirror !== 'undefined') {
                if (editorRef.current.nextSibling) {
                    editorRef.current.nextSibling.remove();
                }
                const editor = CodeMirror.fromTextArea(editorRef.current, {
                    lineNumbers: true,
                    mode: selectedFile.endsWith('.py') ? 'python' : 'javascript',
                    theme: 'monokai',
                    readOnly: false,
                    viewportMargin: Infinity,
                    height: "100%"
                });
                editor.setValue(fileContent);
                editor.refresh();
                
                editor.getWrapperElement().style.height = '100%';
                editor.refresh();

                // Store the editor instance in the ref
                editorRef.current.editor = editor;
            } else {
                console.error('CodeMirror is not defined. Make sure it is properly loaded.');
            }
        }
    }, [selectedFile, fileContent]);

    React.useEffect(() => {
        if (codeMirrorInstanceRef.current) {
            codeMirrorInstanceRef.current.setValue(fileContent);  // Update the CodeMirror content
        }
    }, [fileContent]);

    const checkForNewFiles = React.useCallback(async () => {
        try {
            const response = await fetch('/api/check_new_files', { 
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
    
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
    
            const data = await response.json();
    
            if (data.changed && data.files) {
                setFiles(data.files);
                console.log("File structure updated");
            }
        } catch (error) {
            console.error('Error checking for new files:', error);
        }
    }, []);

    React.useEffect(() => {
        const intervalId = setInterval(checkForNewFiles, 5000); // Check every 5 seconds
        return () => clearInterval(intervalId);
    }, [checkForNewFiles]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const selectedFilesList = Object.keys(selectedFiles).filter(file => selectedFiles[file]);
        const userMessage = selectedFilesList.length > 0
            ? `${input}\n\nSelected files:\n${selectedFilesList.join('\n')}`
            : input;

        setMessages(prevMessages => [...prevMessages, { role: 'user', content: userMessage }]);
        setInput('');

        try {
            if (input.startsWith('/')) {
                const response = await fetch('/api/execute_command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: input.slice(1) })
                });
                const data = await response.json();
                setMessages(prevMessages => [...prevMessages, { role: 'system', content: data.result }]);
            } else {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: userMessage, 
                        selectedFiles: selectedFilesList, 
                        model: selectedModel,
                        command: selectedCommand
                     })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let assistantMessage = '';

                setMessages(prevMessages => [...prevMessages, { role: 'assistant', content: '' }]);

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.slice(6));
                            if (data.error) {
                                throw new Error(data.error);
                            }
                            if (data.updated_files) {
                                setFiles(data.updated_files);
                            } else if (data.is_system) {
                                if (data.is_log) {
                                    setLogs(prevLogs => [...prevLogs, data.chunk]);
                                } else {
                                    setMessages(prevMessages => [...prevMessages, { role: 'system', content: data.chunk }]);
                                }
                            } else if (data.usage) {
                                setMonthlyTokenUsage(data.usage.total_tokens);
                                setMonthlyCost(data.usage.total_cost);
                            } else {
                                assistantMessage += data.chunk || '';
                                setMessages(prevMessages => {
                                    const newMessages = [...prevMessages];
                                    newMessages[newMessages.length - 1].content = assistantMessage;
                                    return newMessages;
                                });
                            }
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Error:', error);
            setMessages(prevMessages => [...prevMessages, { role: 'system', content: `An error occurred: ${error.message}. Please try again.` }]);
            setLogs(prevLogs => [...prevLogs, `Error: ${error.message}`]);
        }
    };

    const handleApiKeySubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('/api/set_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ openai_key: apiKey, anthropic_key: anthropicApiKey })
            });
            const data = await response.json();
            if (data.success) {
                setShowApiKeyModal(false);
            } else {
                throw new Error('Failed to set API key');
            }
        } catch (error) {
            console.error('Error setting API key:', error);
            alert('Failed to set API key. Please try again.');
        }
    };

    const handleFileClick = async (filePath) => {
        const fileExtension = filePath.split('.').pop().toLowerCase();
        const unsupportedExtensions = ['db'];

        if (unsupportedExtensions.includes(fileExtension)) {
            setUnsupportedFile(filePath);
            return;
        }

        try {
            const normalizedPath = filePath.replace(/\\/g, '/');
            const response = await fetch(`/api/file_content?file=${encodeURIComponent(normalizedPath)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setFileContent(data.content);
            setSelectedFile(filePath);
        } catch (error) {
            console.error('Error fetching file content:', error);
            setFileContent(`Error loading file content: ${error.message}`);
        }
    };

    const closeUnsupportedFileModal = () => {
        setUnsupportedFile(null);
    };

    const handleModalClose = async () => {
        if (selectedFile && editorRef.current && editorRef.current.editor) {
            const content = editorRef.current.editor.getValue();
            try {
                const response = await fetch('/api/update_file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file: selectedFile, content: content }),
                });
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                console.log(data.message);
            } catch (error) {
                console.error('Error saving file:', error);
            }
        }
        setSelectedFile(null);
    };

    const handleFileSelect = (filePath) => {
        setSelectedFiles(prev => ({
            ...prev,
            [filePath]: !prev[filePath]
        }));
    };

    const handleModelChange = async (e) => {
        const newModel = e.target.value;
        setSelectedModel(newModel);
        try {
            const response = await fetch('/api/set_model', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: newModel })
            });
            const data = await response.json();
            if (data.success) {
                console.log(data.message);
                if (data.files) {
                    setFiles(data.files);
                }
                setMessages(prevMessages => [
                    ...prevMessages,
                    { role: 'system', content: "Model changed. Reinitializing..." },
                    ...(data.announcements || []).map(announcement => ({ role: 'system', content: announcement }))
                ]);
            } else {
                console.error('Error setting model:', data.error);
                // Revert the selection if there was an error
                setSelectedModel(prevModel => prevModel);
            }
        } catch (error) {
            console.error('Error setting model:', error);
            // Revert the selection if there was an error
            setSelectedModel(prevModel => prevModel);
        }
    };

    const renderFileTree = (structure, path = '') => {
        if (!structure || typeof structure !== 'object') {
            return null;
        }
        return (
            <ul className="pl-4">
                {Object.entries(structure).map(([key, value]) => {
                    const newPath = path ? `${path}/${key}` : key;
                    if (typeof value === 'string') {
                        return (
                            <li key={newPath} className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={selectedFiles[fullPaths[key]] || false}
                                    onChange={() => handleFileSelect(fullPaths[key])}
                                    className="mr-2"
                                />
                                <span 
                                    className="cursor-pointer hover:text-green-300" 
                                    onClick={() => handleFileClick(fullPaths[key])}
                                >
                                    <i className="fas fa-file mr-2"></i>
                                    {key}
                                </span>
                            </li>
                        );
                    } else {
                        return (
                            <li key={newPath}>
                                <details>
                                    <summary className="cursor-pointer hover:text-green-300">
                                        <i className="fas fa-folder mr-2"></i>
                                        {key}
                                    </summary>
                                    {renderFileTree(value, newPath)}
                                </details>
                            </li>
                        );
                    }
                })}
            </ul>
        );
    };

    return (
        <div className="flex flex-col h-screen bg-black text-green-400 font-mono">
            {isInitializing ? (
                <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
                    <div className="bg-gray-800 p-5 rounded-lg text-center">
                        <h2 className="text-xl font-bold mb-4">Setting up the environment...</h2>
                        <p>Please wait while we initialize the system.</p>
                    </div>
                </div>
            ) : (
                <>
                    <header className="p-2 sm:p-4 flex flex-col sm:flex-row justify-between items-center border-b border-green-700">
                        <h1 className="text-xl sm:text-2xl font-bold mb-2 sm:mb-0">papert-lab</h1>
                        <div className="flex flex-col sm:flex-row items-center">
                            <div className="text-xs sm:text-sm mb-2 sm:mb-0 sm:mr-4">
                                <span className="mr-2 sm:mr-4">Tokens: {monthlyTokenUsage.toLocaleString()}</span>
                                <span>Cost: ${monthlyCost.toFixed(4)}</span>
                            </div>
                            <select
                                value={selectedModel || ''}
                                onChange={handleModelChange}
                                className="bg-green-700 text-black px-4 py-2 rounded w-full sm:w-auto"
                            >
                                {/* <option value="" disabled>Select a model</option> */}
                                {models.map((model) => (
                                    <option key={model} value={model}>{model}</option>
                                ))}
                            </select>
                        </div>
                    </header>
            
                    <div className="flex-grow flex flex-col sm:flex-row overflow-hidden">
                        {showFilePanel && (
                            <div className="w-full sm:w-1/4 overflow-y-auto border-b sm:border-b-0 sm:border-r border-green-700 p-2">
                                <h2 className="text-lg sm:text-xl font-bold mb-2">Chat Files</h2>
                                {renderFileTree(files)}
                            </div>
                        )}
                   
                        <div className={`flex-grow flex flex-col ${showFilePanel ? 'sm:w-1/2' : 'w-full'}`}>
                            <div className="flex-grow overflow-y-auto mb-2 sm:mb-4 border border-green-700 p-2">
                                {messages.map((message, index) => (
                                    <div key={index} className="mb-2 whitespace-pre-wrap">
                                        <span className={`font-bold ${getTextColor(message.role)}`}>
                                            {message.role === 'user' ? '> ' : message.role === 'assistant' ? 'AI: ' : 'System: '}
                                        </span>
                                        <MessageContent content={message.content} role={message.role} />
                                    </div>
                                ))}
                                {logs.map((log, index) => (
                                    <div key={`log-${index}`} className="mb-1 text-xs sm:text-sm text-gray-400 whitespace-pre-wrap">
                                        {log}
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>
                        </div>
                    </div>
            
                    <div className="border-t border-green-700 p-2 sm:p-4">
                        <form onSubmit={handleSubmit} className="flex">
                            <div className="command-dropdown" ref={dropdownRef}>
                                <button type="button" onClick={() => setShowCommandDropdown(!showCommandDropdown)} className="bg-green-700 text-black px-2 sm:px-4 py-1 sm:py-2 rounded-l hover:bg-green-600 focus:outline-none">
                                    {selectedCommand} <i className="fas fa-caret-up ml-1"></i>
                                </button>
                                {showCommandDropdown && (
                                    <div className="command-dropdown-content">
                                        <a href="#" onClick={() => handleCommandSelect('code')}>Code</a>
                                        <a href="#" onClick={() => handleCommandSelect('ask')}>Ask</a>
                                        <a href="#" onClick={() => handleCommandSelect('autopilot')}>Autopilot (Beta)</a>
                                        {/* Add more commands as needed */}
                                    </div>
                                )}
                            </div>
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                className="flex-grow bg-gray-800 text-green-400 border border-green-700 rounded-l px-2 sm:px-4 py-1 sm:py-2 focus:outline-none focus:border-green-500"
                                placeholder={`Type a message for ${selectedCommand} command...`}
                            />
                            <button
                                type="submit"
                                className="bg-green-700 text-black px-2 sm:px-4 py-1 sm:py-2 rounded-r hover:bg-green-600 focus:outline-none"
                            >
                                Send
                            </button>
                        </form>
                    </div>
            
                    {/* Floating control buttons */}
                    <div className="fixed right-4 top-1/2 transform -translate-y-1/2 flex flex-col space-y-2 z-50">
                        <button
                            onClick={() => setShowFilePanel(!showFilePanel)}
                            className="bg-green-700 text-black p-2 rounded-full hover:bg-green-600 focus:outline-none"
                            title="Toggle File Panel"
                        >
                            <i className="fas fa-folder"></i>
                        </button>
                        <button
                            onClick={() => window.open('/settings', '_blank')}
                            className="bg-green-700 text-black p-2 rounded-full hover:bg-green-600 focus:outline-none"
                            title="Settings"
                        >
                            <i className="fas fa-gear"></i>
                        </button>
                    </div>
            
                    {/* API Key Modal */}
                    {showApiKeyModal && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
                            <div className="bg-gray-800 p-5 rounded-lg w-full max-w-md">
                                <h2 className="text-xl font-bold mb-4">Enter your API Keys</h2>
                                <form onSubmit={handleApiKeySubmit}>
                                    <input
                                        type="text"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        className="bg-gray-700 text-white border border-gray-600 rounded px-4 py-2 w-full mb-4"
                                        placeholder="OpenAI API Key"
                                    />
                                    <input
                                        type="text"
                                        value={anthropicApiKey}
                                        onChange={(e) => setAnthropicApiKey(e.target.value)}
                                        className="bg-gray-700 text-white border border-gray-600 rounded px-4 py-2 w-full mb-4"
                                        placeholder="Anthropic API Key"
                                    />
                                    <button
                                        type="submit"
                                        className="bg-green-500 text-black px-4 py-2 rounded hover:bg-green-600 w-full"
                                    >
                                        Submit
                                    </button>
                                </form>
                            </div>
                        </div>
                    )}

                    {/* Unsupported File Modal */}
                    {unsupportedFile && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                            <div className="bg-gray-800 p-5 rounded-lg max-w-md w-full">
                                <h2 className="text-xl font-bold mb-4">Unsupported File Format</h2>
                                <p>The file "{unsupportedFile}" is not supported for editing in this interface.</p>
                                <div className="mt-4 flex justify-end">
                                    <button
                                        onClick={closeUnsupportedFileModal}
                                        className="bg-green-700 text-black px-4 py-2 rounded hover:bg-green-600"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
            
                    {/* File Editor Modal */}
                    {selectedFile && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                            <div className="bg-gray-800 p-5 rounded-lg w-full max-w-4xl h-5/6 flex flex-col relative">
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className="text-xl font-bold">{selectedFile}</h2>
                                    <button
                                        onClick={handleModalClose}
                                        className="bg-red-500 text-white px-2 py-1 rounded"
                                    >
                                        Close
                                    </button>
                                </div>
                                <div className="flex-grow overflow-hidden bg-gray-900 rounded relative">
                                    <textarea 
                                        ref={editorRef} 
                                        defaultValue={fileContent}  
                                        className="w-full h-full bg-gray-900 text-green-400 font-mono resize-none focus:outline-none p-2 absolute inset-0"
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

ReactDOM.render(<App />, document.getElementById('root'));