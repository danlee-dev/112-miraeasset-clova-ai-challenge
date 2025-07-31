import React, { useState } from 'react';
import { useUser } from '../../context/UserContext';
import API_BASE_URL from '../../config/api';
import './NaturalLanguageProfileSetup.css';

const NaturalLanguageProfileSetup = ({ onComplete }) => {
  const { saveUser } = useUser();
  const [currentStep, setCurrentStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [conversation, setConversation] = useState([
    {
      type: 'assistant',
      message: '안녕하세요! 개인화된 투자 서비스를 위해 몇 가지 정보가 필요합니다. 편하게 자연어로 말씀해 주세요.',
      timestamp: new Date()
    },
    {
      type: 'assistant', 
      message: '먼저 간단한 자기소개를 해주세요. 이름, 나이, 투자 경험 등을 자유롭게 말씀해 주시면 됩니다.',
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [extractedInfo, setExtractedInfo] = useState({});
  const [missingFields, setMissingFields] = useState([]);

  // 필수 정보 필드들
  const requiredFields = {
    name: '이름',
    age: '나이', 
    investment_experience: '투자 경험',
    risk_tolerance: '위험 허용도',
    investment_goals: '투자 목표',
    preferred_sectors: '관심 섹터',
    investment_style: '투자 스타일',
    investment_amount_range: '투자 금액 범위'
  };

  const sendToLLM = async (userInput, previousInfo = {}) => {
    try {
      setIsProcessing(true);
      
      const response = await fetch(`${API_BASE_URL}/api/chat/profile-extraction`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userInput,
          previous_info: previousInfo,
          required_fields: Object.keys(requiredFields)
        })
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('LLM 호출 실패:', error);
      return { error: '처리 중 오류가 발생했습니다.' };
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUserInput = async () => {
    if (!inputText.trim()) return;

    // 사용자 메시지 추가
    const userMessage = {
      type: 'user',
      message: inputText,
      timestamp: new Date()
    };

    setConversation(prev => [...prev, userMessage]);
    setInputText('');

    // LLM으로 정보 추출
    const result = await sendToLLM(inputText, extractedInfo);

    if (result.error) {
      const errorMessage = {
        type: 'assistant',
        message: result.error,
        timestamp: new Date()
      };
      setConversation(prev => [...prev, errorMessage]);
      return;
    }

    // 추출된 정보 업데이트
    const newExtractedInfo = { ...extractedInfo, ...result.extracted_info };
    setExtractedInfo(newExtractedInfo);

    // 부족한 정보 확인
    const missing = Object.keys(requiredFields).filter(
      field => !newExtractedInfo[field] || 
      (Array.isArray(newExtractedInfo[field]) && newExtractedInfo[field].length === 0)
    );

    setMissingFields(missing);

    let assistantMessage;

    if (missing.length > 0) {
      // 부족한 정보가 있으면 추가 질문
      const missingFieldNames = missing.map(field => requiredFields[field]).join(', ');
      assistantMessage = {
        type: 'assistant',
        message: `좋습니다! 다음 정보가 더 필요합니다: ${missingFieldNames}. 추가로 알려주시겠어요?`,
        timestamp: new Date()
      };
    } else {
      // 모든 정보가 완성되면 확인 메시지
      assistantMessage = {
        type: 'assistant',
        message: '완벽합니다! 모든 정보를 잘 수집했습니다. 확인해주세요.',
        timestamp: new Date(),
        showSummary: true
      };
      setCurrentStep(2);
    }

    setConversation(prev => [...prev, assistantMessage]);
  };

  const handleConfirm = async () => {
    try {
      setIsProcessing(true);

      // 사용자 ID 생성
      const userId = `${extractedInfo.name}_${Date.now()}`;
      
      // 사용자 프로필 저장
      const userProfile = {
        user_id: userId,
        ...extractedInfo,
        portfolio: [] // 초기에는 빈 포트폴리오
      };

      // 백엔드에 저장
      const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          ...extractedInfo
        })
      });

      if (!response.ok) {
        throw new Error('프로필 저장에 실패했습니다.');
      }

      // 로컬 컨텍스트에 저장
      saveUser(userProfile);

      // 완료 콜백 호출
      if (onComplete) {
        onComplete(userProfile);
      }

    } catch (error) {
      console.error('프로필 저장 실패:', error);
      alert('프로필 저장에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserInput();
    }
  };

  const formatFieldValue = (field, value) => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return value;
  };

  return (
    <div className="natural-profile-setup">
      <div className="setup-container">
        <div className="setup-header">
          <h2>🤖 AI 프로필 설정 어시스턴트</h2>
          <div className="step-indicator">
            <span className={currentStep >= 1 ? 'active' : ''}>1</span>
            <span className={currentStep >= 2 ? 'active' : ''}>2</span>
          </div>
        </div>

        {currentStep === 1 && (
          <div className="conversation-container">
            <div className="messages">
              {conversation.map((msg, index) => (
                <div key={index} className={`message ${msg.type}`}>
                  <div className="message-content">
                    {msg.message}
                    {msg.showSummary && (
                      <div className="info-summary">
                        <h4>수집된 정보:</h4>
                        {Object.entries(extractedInfo).map(([field, value]) => (
                          <div key={field} className="info-item">
                            <strong>{requiredFields[field]}:</strong> {formatFieldValue(field, value)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="message-time">
                    {msg.timestamp.toLocaleTimeString('ko-KR', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </div>
                </div>
              ))}
              
              {isProcessing && (
                <div className="message assistant">
                  <div className="message-content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="input-container">
              <div className="progress-info">
                <span className="required-fields">
                  필요 정보: {Object.keys(requiredFields).length - missingFields.length}/{Object.keys(requiredFields).length}
                </span>
                {missingFields.length > 0 && (
                  <span className="missing-fields">
                    부족: {missingFields.map(f => requiredFields[f]).join(', ')}
                  </span>
                )}
              </div>
              
              <div className="input-area">
                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="편하게 자연어로 입력해주세요... (예: 안녕하세요, 저는 김철수이고 나이는 30살입니다. 투자 경험은 초보이고...)"
                  rows={3}
                  disabled={isProcessing || currentStep === 2}
                />
                <button 
                  onClick={handleUserInput}
                  disabled={!inputText.trim() || isProcessing || currentStep === 2}
                  className="send-button"
                >
                  전송
                </button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="confirmation-step">
            <h3>정보 확인 및 저장</h3>
            <div className="final-summary">
              {Object.entries(extractedInfo).map(([field, value]) => (
                <div key={field} className="summary-item">
                  <label>{requiredFields[field]}:</label>
                  <span>{formatFieldValue(field, value)}</span>
                </div>
              ))}
            </div>
            
            <div className="action-buttons">
              <button 
                onClick={() => setCurrentStep(1)}
                className="btn-back"
                disabled={isProcessing}
              >
                수정하기
              </button>
              <button 
                onClick={handleConfirm}
                className="btn-confirm"
                disabled={isProcessing}
              >
                {isProcessing ? '저장 중...' : '확인 및 저장'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NaturalLanguageProfileSetup;
