import { Routes, Route } from 'react-router-dom'
import { PipelineProvider } from './context/PipelineContext'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import UploadPage from './components/UploadPage'
import PipelineControls from './components/PipelineControls'
import ImageGrid from './components/ImageGrid'
import ReviewModal from './components/ReviewModal'

function App() {
  return (
    <PipelineProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="pipeline" element={<PipelineControls />} />
          <Route path="review/:status" element={<ImageGrid />} />
          <Route path="review/:status/:id" element={<ReviewModal />} />
        </Route>
      </Routes>
    </PipelineProvider>
  )
}

export default App