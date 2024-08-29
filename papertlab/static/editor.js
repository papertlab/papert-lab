window.Editor = ({ file, content, onClose, onSave }) => {
    const editorRef = React.useRef(null);
    const changeEditorRef = React.useRef(null);
    const [editorInstance, setEditorInstance] = React.useState(null);
    const [showChangeModal, setShowChangeModal] = React.useState(false);
    const [proposedChanges, setProposedChanges] = React.useState('');
    const [isLoading, setIsLoading] = React.useState(false);
    const [selectedCode, setSelectedCode] = React.useState('');
    const [selectedRange, setSelectedRange] = React.useState(null);
    const [saveMessage, setSaveMessage] = React.useState('');

    const handleSave = React.useCallback((cm) => {
        if (cm) {
            cm.save();  // This saves the content back to the textarea
            const currentContent = cm.getValue();
            onSave(currentContent);
            setSaveMessage('File saved successfully!');
            setTimeout(() => setSaveMessage(''), 2000);  // Clear message after 2 seconds
        }
    }, [onSave]);

    React.useEffect(() => {
        if (editorRef.current) {
            const editor = CodeMirror.fromTextArea(editorRef.current, {
                lineNumbers: true,
                mode: getLanguageMode(file),
                theme: 'monokai',
                autoCloseBrackets: true,
                matchBrackets: true,
                indentUnit: 4,
                tabSize: 4,
                indentWithTabs: false,
                foldGutter: true,
                gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
                extraKeys: {
                    'Ctrl-/': 'toggleComment',
                    'Cmd-/': 'toggleComment',
                    'Ctrl-F': 'findPersistent',
                    'Cmd-F': 'findPersistent',
                    'Ctrl-H': 'replace',
                    'Cmd-Option-F': 'replace',
                    'Ctrl-I': 'inlineEdit',
                    'Cmd-I': 'inlineEdit',
                    'Ctrl-S': (cm) => { handleSave(cm); return false; },
                    'Cmd-S': (cm) => { handleSave(cm); return false; },
                },
                lint: true,
                styleActiveLine: true,
            });

            editor.setValue(content);
            editor.setSize('100%', '100%');

            CodeMirror.commands.inlineEdit = (cm) => {
                const selection = cm.getSelection();
                if (selection) {
                    setSelectedCode(selection);
                    setSelectedRange(cm.listSelections()[0]);
                    const dialogCallback = (result) => {
                        if (result) {
                            handleInlineEdit(selection, result);
                        }
                    };
                    cm.openDialog(
                        'Describe the changes you want to make: <input type="text" style="width: 60%;">',
                        dialogCallback,
                        { bottom: true }
                    );
                } else {
                    console.log('No code selected');
                }
            };

            setEditorInstance(editor);

            // Refresh the editor after a short delay to ensure proper sizing
            setTimeout(() => editor.refresh(), 100);

            return () => {
                editor.toTextArea();
            };
        }
    }, [file, content]);

    const getLanguageMode = (filename) => {
        const extension = filename.split('.').pop().toLowerCase();
        switch (extension) {
            case 'js': return 'javascript';
            case 'py': return 'python';
            case 'html': return 'htmlmixed';
            case 'css': return 'css';
            default: return 'javascript';
        }
    };

    const handleClose = () => {
        if (editorInstance) {
            const currentContent = editorInstance.getValue();
            onSave(currentContent);
        }
        onClose();
    };

    React.useEffect(() => {
        if (showChangeModal && changeEditorRef.current && !isLoading) {
            const changeEditor = CodeMirror.fromTextArea(changeEditorRef.current, {
                lineNumbers: true,
                mode: getLanguageMode(file),
                theme: 'monokai',
                readOnly: true,
                viewportMargin: Infinity,
                lineWrapping: true
            });
            changeEditor.setValue(proposedChanges);
            changeEditor.refresh();

            return () => {
                changeEditor.toTextArea();
            };
        }
    }, [showChangeModal, proposedChanges, file, isLoading]);

    const handleInlineEdit = async (selectedCode, inlineEditContent) => {
        setIsLoading(true);
        setShowChangeModal(true);
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: inlineEditContent,
                    selectedCode: selectedCode,
                    file: file,
                    command: 'inline'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let updatedCode = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(5));
                            if (data.updatedCode) {
                                updatedCode = data.updatedCode;
                            }
                        } catch (e) {
                            console.error('Error parsing JSON:', e);
                        }
                    }
                }
            }

            if (updatedCode) {
                setProposedChanges(updatedCode);
            } else {
                console.log('No updated code received');
            }
        } catch (error) {
            console.error('Error during inline edit:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const applyChanges = () => {
        const replaceContent = extractReplacementContent(proposedChanges);
        if (replaceContent && editorInstance && selectedRange) {
            editorInstance.setSelection(selectedRange.anchor, selectedRange.head);
            editorInstance.replaceSelection(replaceContent);
        }
        resetChangeState();
    };

    const resetChangeState = () => {
        setShowChangeModal(false);
        setProposedChanges('');
        setSelectedCode('');
        setSelectedRange(null);
    };

    const extractReplacementContent = (changes) => {
        const lines = changes.split('\n');
     
        let replaceContent = [];

        for (const line of lines) {
      
            replaceContent.push(line);
            
        }

        return replaceContent.join('\n');
    };

    const ChangeModal = () => (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-4 rounded-lg w-1/2 h-2/3 flex flex-col">
                <h2 className="text-xl font-bold mb-4">Proposed Changes</h2>
                <div className="flex-grow overflow-hidden mb-4 relative">
                {isLoading ? (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-green-400"></div>
                        </div>
                    ) : (
                    <div className="absolute inset-0 overflow-auto">
                        <textarea ref={changeEditorRef} defaultValue={proposedChanges} className="h-full w-full" />
                    </div>
                    )}
                </div>
                {isLoading ? (
                    <div className="flex justify-end"></div>
                ) : (
                <div className="flex justify-end">
                    <button
                        onClick={applyChanges}
                        className="bg-green-500 text-white px-4 py-2 rounded mr-2 hover:bg-green-600"
                        disabled={isLoading}
                    >
                        Accept
                    </button>
                    <button
                        onClick={resetChangeState}
                        className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                    >
                        Reject
                    </button>
                </div>
                )}
            </div>
        </div>
    );

    return (
        <>
            <div className="sticky top-0 z-10 bg-gray-800 flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold">{file}</h2>
                <div>
                {saveMessage && <span className="text-green-400 mr-4">{saveMessage}</span>}
                    <button
                        onClick={handleClose}
                        className="bg-red-700 text-black px-2 py-1 rounded hover:bg-red-600 focus:outline-none"
                    >
                       <i class="far fa-window-close"></i>
                    </button>
                </div>
            </div>
            <div className="flex-grow overflow-hidden z-10">
                <textarea
                    ref={editorRef}
                    defaultValue={content}
                    className="w-full h-full"
                    style={{ display: 'none' }}
                />
            </div>

            {showChangeModal && <ChangeModal />}
        </>
    );
};