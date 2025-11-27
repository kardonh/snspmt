import React from 'react'
import { useState, useEffect,useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { createOrderData, saveOrderForCheckout } from '../utils/orderManager'
import PlatformGrid from '../components/home/PlatformGrid'
import ServiceTypeSelector from '../components/home/ServiceTypeSelector'
import PackageList from '../components/home/PackageList'
import PackageDetailView from '../components/home/PackageDetailView'
import VariantList from '../components/home/VariantList'
import OrderForm from '../components/home/OrderForm'
import './Home.css'

function Home2() {
  const navigate = useNavigate()
  const [selectedPlatform, setSelectedPlatform] = useState('recommended')
  const [selectedTab, setSelectedTab] = useState('korean')
  const [selectedService, setSelectedService] = useState(null)
  const [selectedPackage, setSelectedPackage] = useState(null)
  const [selectedVariant, setSelectedVariant] = useState(null)
  const [selectedPackageDetail, setSelectedPackageDetail] = useState(null)
  const [categories, setCategories] = useState([])
  const [products, setProducts] = useState([])
  const [packages, setPackages] = useState([])
  const [variants, setVariants] = useState([])
  const [currentStep, setCurrentStep] = useState(null)

  // Refs for scrolling
  const platformRef = useRef(null)
  const serviceRef = useRef(null)
  const variantRef = useRef(null)
  const orderFormRef = useRef(null)

  const scrollToRef = (ref) => {
    if (ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }


  const categoryColors = {
    instagram: '#e4405f',
    youtube: '#ff0000',
    facebook: '#1877f2',
    tiktok: '#000000',
    naver: '#03c75a'
  }

  // api calls
  function handleFetchCategories() {
    api.get('/categories')
      .then(response => {
        const payload = Array.isArray(response.data) ? response.data : response.data?.categories || []
        setCategories(payload)
      })
      .catch(error => console.error('Error fetching categories:', error))
  }

  function handleFetchProducts(category_id) {
    api.get(`/products?category_id=${category_id}`)
      .then(response => {
        const payload = Array.isArray(response.data) ? response.data : response.data?.products || []
        setProducts(payload)
      })
      .catch(error => console.error('Error fetching products:', error))
  }

  function handleFetchPackages() {
    api.get('/packages')
      .then(response => {
        const payload = response.data?.packages || []
        setPackages(payload)
      })
      .catch(error => console.error('Error fetching packages:', error))
  }

  function handleFetchVariants(product_id) {
    api.get(`/product-variants?product_id=${product_id}`)
      .then(response => {
        const payload = response.data?.variants || []
        setVariants(payload)
      })
      .catch(error => console.error('Error fetching variants:', error))
  }

  // 

  const handlePlatformSelect = (platformId) => {
    setSelectedPlatform(platformId)
    setCurrentStep(2)
    setSelectedService(null)
    setSelectedVariant(null)
    setSelectedPackage(null)
    setSelectedPackageDetail(null)
    setTimeout(() => scrollToRef(serviceRef), 100)
  }

  const handleServiceSelect = (serviceId) => {
    setSelectedService(serviceId)
    handleFetchVariants(serviceId)
    setCurrentStep(3)
    setTimeout(() => scrollToRef(variantRef), 100)
  }

  const handlePackageSelect = (packageId) => {
    setSelectedPackage(packageId)
    const packageDetail = packages.find(pkg => pkg.package_id === packageId)
    setSelectedPackageDetail(packageDetail)
    setCurrentStep(3)
    setTimeout(() => scrollToRef(variantRef), 100)
  }

  const handleVariantSelect = (variant) => {
    setSelectedVariant(variant)
    setCurrentStep(4)
    setTimeout(() => scrollToRef(orderFormRef), 100)
  }

  const handleClosePackageDetail = () => {
    setSelectedPackageDetail(null)
    setSelectedPackage(null)
    setCurrentStep(2)
  }

  const handleBackStep = () => {
    if (currentStep === 2) {
      setCurrentStep(1)
      setSelectedPlatform('recommended')
      setSelectedService(null)
      setSelectedPackage(null)
      setSelectedPackageDetail(null)
      setSelectedVariant(null)
    } else if (currentStep === 3) {
      setCurrentStep(2)
      setSelectedService(null)
      setSelectedVariant(null)
      setSelectedPackageDetail(null)
      setSelectedPackage(null)
    } else if (currentStep === 4) {
      setCurrentStep(3)
      setSelectedVariant(null)
    }
  }

  const handleNextStep = () => {
    if (currentStep === null || currentStep === 1) {
      if (selectedPlatform) {
        setCurrentStep(2)
      }
    } else if (currentStep === 2) {
      if (selectedPackage || selectedService) {
        setCurrentStep(3)
      }
    } else if (currentStep === 3) {
      if (selectedPackageDetail || selectedVariant) {
        setCurrentStep(4)
      }
    }
  }

  const canGoNext = () => {
    if (currentStep === null || currentStep === 1) return selectedPlatform
    if (currentStep === 2) return selectedPackage || selectedService
    if (currentStep === 3) return selectedPackageDetail || selectedVariant
    return false
  }

  const handleOrderSubmit = (orderType, formData) => {
    const category = categories.find(c => c.category_id === selectedPlatform)

    let orderData
    if (orderType === 'package') {
      orderData = createOrderData({
        type: 'package',
        category,
        packageData: selectedPackageDetail,
        link: formData.link
      })
    } else {
      const product = products.find(p => p.product_id === selectedService)
      orderData = createOrderData({
        type: 'product',
        category,
        product,
        variant: selectedVariant,
        quantity: formData.quantity,
        link: formData.link,
        comments: formData.comments
      })
    }

    if (saveOrderForCheckout(orderData)) {
      navigate('/checkout')
    }
  }


  useEffect(() => {
    Promise.all([handleFetchCategories(), handleFetchPackages()])
    if (selectedPlatform && selectedPlatform !== 'recommended') {
      handleFetchProducts(selectedPlatform)
    }
  }, [selectedPlatform])


  return (
    <div>
      {/* Step 1: Platform Selection */}
      <div ref={platformRef}>
        <PlatformGrid
          categories={categories}
          selectedPlatform={selectedPlatform}
          onSelectPlatform={handlePlatformSelect}
          categoryColors={categoryColors}
        />
      </div>

      {/* Step 2: Package List or Service Selector */}
      {selectedPlatform === 'recommended' && (
        <div ref={serviceRef}>
          <PackageList
            packages={packages}
            selectedPackage={selectedPackage}
            onSelectPackage={handlePackageSelect}
          />
        </div>
      )}

      {selectedPlatform && selectedPlatform !== 'recommended' && (
        <div ref={serviceRef}>
          <ServiceTypeSelector
            categories={categories}
            selectedPlatform={selectedPlatform}
            selectedTab={selectedTab}
            onTabChange={setSelectedTab}
            products={products}
            selectedService={selectedService}
            onServiceSelect={handleServiceSelect}
          />
        </div>
      )}

      {/* Step 3: Package Detail or Variant List */}
      {selectedPackageDetail && (
        <div ref={variantRef}>
          <PackageDetailView
            packageDetail={selectedPackageDetail}
            onClose={handleClosePackageDetail}
          />
        </div>
      )}

      {selectedService && variants.length > 0 && selectedPlatform !== 'recommended' && (
        <div ref={variantRef}>
          <VariantList
            variants={variants}
            selectedVariant={selectedVariant}
            onSelectVariant={handleVariantSelect}
          />
        </div>
      )}

      {/* Step 4: Order Form */}
      {selectedPackageDetail && (
        <div ref={orderFormRef}>
          <OrderForm
            packageDetail={selectedPackageDetail}
            category={categories.find(c => c.category_id === selectedPackageDetail.category_id)}
            onSubmit={(formData) => handleOrderSubmit('package', formData)}
          />
        </div>
      )}

      {selectedVariant && (
        <div ref={orderFormRef}>
          <OrderForm
            variant={selectedVariant}
            category={categories.find(c => c.category_id === selectedPlatform)}
            onSubmit={(formData) => handleOrderSubmit('product', formData)}
          />
        </div>
      )}
    </div>
  )
}

export default Home2