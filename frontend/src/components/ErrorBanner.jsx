export default function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="banner banner-error" role="alert">
      <strong>Error:</strong> {message}
    </div>
  );
}
