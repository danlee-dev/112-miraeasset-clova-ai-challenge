import React, { useState, useRef, useEffect } from 'react';
import { Send, Home } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid'; // uuid 패키지 설치 필요

const MobileChatbot = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: '안녕하세요! 😊\n미래에셋증권 투자상담 챗봇 더미입니다.\n궁금한 사항을 입력해주세요.',
      timestamp: new Date().toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      }),
      isWelcome: true
    }
  ]);
  
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = {
      id: uuidv4(),
      type: 'user',
      content: inputText,
      timestamp: new Date().toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // FastAPI 연동 시 아래 주석 해제
      // TODO: FastAPI 연동 시 주석 해제
      // const response = await fetch('http://localhost:8000/chat', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({ message: inputText })
      // });
      // const data = await response.json();

      // 임시 더미 응답
      setTimeout(() => {
        const botMessage = {
          id: uuidv4(),
          type: 'bot',
          content: `"${inputText}"에 대한 답변입니다. 더 자세한 정보가 필요하시면 언제든 문의해주세요.`,
          timestamp: new Date().toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          })
        };
        
        setMessages(prev => [...prev, botMessage]);
        setIsLoading(false);
        inputRef.current?.focus(); // 메시지 전송 후 input에 포커스
      }, 1000);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 max-w-md mx-auto">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">m</span>
          </div>
          <span className="font-semibold text-gray-900">m.Talk</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-xs lg:max-w-md">
              {message.type === 'system' && (
                <div className="bg-gray-100 rounded-lg p-3 text-sm text-gray-700">
                  {message.content}
                </div>
              )}
              
              {message.type === 'user' && (
                <div className="flex items-end space-x-2">
                  <span className="text-xs text-gray-500 mb-1">{message.timestamp}</span>
                  <div className="bg-blue-500 text-white rounded-lg px-3 py-2 text-sm">
                    {message.content}
                  </div>
                </div>
              )}
              
              {message.type === 'bot' && (
                <div className="flex items-start space-x-2">
                  <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center mt-1">
                    <span className="text-white text-xs">😊</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium">m.Talk</span>
                      <span className="text-xs text-gray-500">{message.timestamp}</span>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-3 text-sm text-gray-700">
                      {message.content.split('\n').map((line, index) => (
                        <div key={index}>{line}</div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-2">
              <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                <span className="text-white text-xs">😊</span>
              </div>
              <div className="bg-gray-100 rounded-lg p-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <div className="flex items-center space-x-2">
          <button className="p-2 text-gray-400 hover:text-gray-600">
            <Home size={20} />
          </button>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="궁금한 사항을 입력해 주세요"
              className="w-full px-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
              aria-label="메시지 입력"
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!inputText.trim() || isLoading}
            className="p-2 text-blue-500 hover:text-blue-600 disabled:text-gray-400 disabled:cursor-not-allowed"
            type="button"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default MobileChatbot;