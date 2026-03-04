import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import FileResult from './FileResult';

const createObjectURLMock = vi.fn(() => 'blob:test-url');
const revokeObjectURLMock = vi.fn();

vi.mock('lib/components/display/icons/Iconified', () => ({
  default: () => <span>icon</span>
}));

vi.mock('use-context-selector', async importOriginal => {
  const actual: any = await importOriginal();

  return {
    ...actual,
    useContextSelector: (_ctx: unknown, selector: (value: any) => any) =>
      selector({
        i18next: {
          t: (key: string, options?: Record<string, string | number>) => {
            if (key === 'actions.result.file.title') {
              return `${options?.actionName ?? 'Unknown'} has provided a file`;
            }

            if (key === 'actions.result.file.description') {
              return `The action ${options?.actionName ?? 'Unknown'} has provided a file for download.`;
            }

            return key;
          }
        }
      })
  };
});

describe('FileResult', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    createObjectURLMock.mockClear();
    revokeObjectURLMock.mockClear();

    vi.stubGlobal(
      'URL',
      Object.assign(URL, {
        createObjectURL: createObjectURLMock,
        revokeObjectURL: revokeObjectURLMock
      })
    );
  });

  it('renders title/description and stats rows for valid output', async () => {
    vi.spyOn(crypto.subtle, 'digest').mockResolvedValue(
      Uint8Array.from([0xde, 0xad, 0xbe, 0xef]).buffer as ArrayBuffer
    );

    render(
      <FileResult
        result={
          {
            action: { name: 'Test Action' },
            output: {
              data: btoa('hello'),
              mime_type: 'text/plain',
              file_name: 'hello.txt'
            }
          } as any
        }
      />
    );

    expect(screen.getByText('Test Action has provided a file')).toBeInTheDocument();
    expect(screen.getByText('The action Test Action has provided a file for download.')).toBeInTheDocument();

    expect(screen.getByText('actions.result.file.stats.label.decoded_size')).toBeInTheDocument();
    expect(screen.getByText('5 B')).toBeInTheDocument();
    expect(screen.getByText('actions.result.file.stats.label.decoded_bytes')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('actions.result.file.stats.label.base64_length')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('deadbeef')).toBeInTheDocument();
    });
  });

  it('disables download button when output data is missing', () => {
    render(
      <FileResult
        result={
          {
            action: { name: 'No Data Action' },
            output: undefined
          } as any
        }
      />
    );

    const button = screen.getByRole('button', { name: /download/i });
    expect(button).toBeDisabled();
    expect(screen.queryByText('actions.result.file.stats.label.decoded_size')).not.toBeInTheDocument();
  });

  it('downloads file when download button is clicked', async () => {
    vi.spyOn(crypto.subtle, 'digest').mockResolvedValue(new Uint8Array([1, 2, 3, 4]).buffer as ArrayBuffer);

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const appendChildSpy = vi.spyOn(document.body, 'appendChild');
    const removeChildSpy = vi.spyOn(document.body, 'removeChild');

    render(
      <FileResult
        result={
          {
            action: { name: 'Test Action' },
            output: {
              data: btoa('hello'),
              mime_type: 'text/plain',
              file_name: 'hello.txt'
            }
          } as any
        }
      />
    );

    await waitFor(() => {
      expect(screen.getByText('01020304')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /download/i }));

    await waitFor(() => {
      expect(createObjectURLMock).toHaveBeenCalledOnce();
      expect(clickSpy).toHaveBeenCalledOnce();

      const appendedAnchor = appendChildSpy.mock.calls.some(
        ([node]) => node instanceof HTMLAnchorElement && node.download === 'hello.txt'
      );
      const removedAnchor = removeChildSpy.mock.calls.some(
        ([node]) => node instanceof HTMLAnchorElement && node.download === 'hello.txt'
      );

      expect(appendedAnchor).toBe(true);
      expect(removedAnchor).toBe(true);
      expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:test-url');
    });
  });
});
