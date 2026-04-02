import React from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { FileCheck, Hash, Clock } from 'lucide-react';

interface StatusPanelProps {
  uploadStatus: 'idle' | 'uploading' | 'success' | 'error';
  fileName?: string;
  chunksProcessed?: number;
  sessionId?: string;
  processingTime?: number;
}

export function StatusPanel({ 
  uploadStatus, 
  fileName, 
  chunksProcessed, 
  sessionId,
  processingTime 
}: StatusPanelProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'uploading':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'success':
        return 'Processing Complete';
      case 'error':
        return 'Processing Failed';
      case 'uploading':
        return 'Processing...';
      default:
        return 'Ready';
    }
  };

  return (
    <Card className="w-80 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <FileCheck className="h-5 w-5 text-muted-foreground" />
        <h3 className="font-medium">Session Status</h3>
      </div>
      
      <div className="space-y-3">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge 
              variant="outline" 
              className={getStatusColor(uploadStatus)}
            >
              {getStatusText(uploadStatus)}
            </Badge>
          </div>
          
          {fileName && (
            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">Document</span>
              <p className="text-sm font-medium truncate" title={fileName}>
                {fileName}
              </p>
            </div>
          )}
        </div>
        
        {(chunksProcessed !== undefined || processingTime !== undefined || sessionId) && (
          <>
            <Separator />
            <div className="space-y-2">
              {chunksProcessed !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Chunks Processed</span>
                  <div className="flex items-center gap-1">
                    <Hash className="h-3 w-3 text-muted-foreground" />
                    <span className="text-sm font-medium">{chunksProcessed}</span>
                  </div>
                </div>
              )}
              
              {processingTime !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Processing Time</span>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    <span className="text-sm font-medium">{processingTime}ms</span>
                  </div>
                </div>
              )}
              
              {sessionId && (
                <div className="space-y-1">
                  <span className="text-sm text-muted-foreground">Session ID</span>
                  <p className="text-xs font-mono bg-muted p-2 rounded border">
                    {sessionId}
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}