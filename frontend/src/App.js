import React from 'react'
import { Routes, Route } from 'react-router-dom'
import HomePage from './HomePage'
import RegisterPage from './RegisterPage'
import ResetPasswordPage from './ResetPasswordPage'
import ConsoleApp from './ConsoleApp'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/app" element={<ConsoleApp />} />
      <Route path="*" element={<HomePage />} />
    </Routes>
  )
}
