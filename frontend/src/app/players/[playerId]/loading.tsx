export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="h-72 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
        <div className="h-72 bg-gray-200 dark:bg-gray-700 rounded-2xl lg:col-span-2" />
      </div>
      <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-2xl" />
    </div>
  );
}
