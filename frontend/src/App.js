import React from 'react'
import { Routes, Route } from 'react-router-dom'
import HomePage from './HomePage'
import RegisterPage from './RegisterPage'
import ResetPasswordPage from './ResetPasswordPage'
import ConsoleApp from './ConsoleApp'
import QuestionnaireResponsePage from './QuestionnaireResponsePage'
import AgreementSignPage from './AgreementSignPage'
import TrustCenterPage from './TrustCenterPage'
import AuditorPortalPage from './AuditorPortalPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/app" element={<ConsoleApp />} />
      <Route path="/questionnaire/:token" element={<QuestionnaireResponsePage />} />
      <Route path="/agreement/:token" element={<AgreementSignPage />} />
      <Route path="/trust" element={<TrustCenterPage />} />
      <Route path="/auditor/:token" element={<AuditorPortalPage />} />
      <Route path="*" element={<HomePage />} />
    </Routes>
  )
}
